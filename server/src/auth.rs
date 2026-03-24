use std::fs;
use std::path::PathBuf;

use argon2::password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString};
use argon2::Argon2;
use chrono::{DateTime, Utc};
use rand_core::OsRng;
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

const DEFAULT_ADMIN_NAME: &str = "System Admin";
const DEFAULT_ADMIN_USERNAME: &str = "admin";
const DEFAULT_ADMIN_PASSWORD: &str = "admin123456";
const SESSION_TTL_SECONDS: i64 = 30 * 24 * 60 * 60;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum UserRole {
    Admin,
    User,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct UserProfile {
    pub id: String,
    pub name: String,
    pub username: String,
    pub role: UserRole,
    pub active: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AuthSession {
    pub token: String,
    pub user: UserProfile,
}

#[derive(Debug, Clone)]
pub struct AuthStore {
    db_path: PathBuf,
}

#[derive(Debug)]
struct StoredUser {
    profile: UserProfile,
    password_hash: String,
}

impl UserRole {
    pub fn is_admin(&self) -> bool {
        matches!(self, Self::Admin)
    }

    fn as_str(&self) -> &'static str {
        match self {
            Self::Admin => "admin",
            Self::User => "user",
        }
    }

    fn from_str(value: &str) -> Result<Self, String> {
        match value {
            "admin" => Ok(Self::Admin),
            "user" => Ok(Self::User),
            other => Err(format!("unknown user role: {other}")),
        }
    }
}

impl AuthStore {
    pub fn new(db_path: PathBuf) -> Self {
        Self { db_path }
    }

    pub fn initialize(&self) -> Result<(), String> {
        if let Some(parent) = self.db_path.parent() {
            fs::create_dir_all(parent).map_err(|error| format!("failed to create auth store directory: {error}"))?;
        }

        let connection = self.open()?;
        connection
            .execute_batch(
                "
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                ",
            )
            .map_err(|error| format!("failed to initialize auth store: {error}"))?;

        self.cleanup_expired_sessions_with_connection(&connection)?;
        self.ensure_bootstrap_admin_with_connection(&connection)
    }

    pub fn authenticate(&self, username: &str, password: &str) -> Result<AuthSession, String> {
        let connection = self.open()?;
        self.cleanup_expired_sessions_with_connection(&connection)?;

        let stored_user = self
            .find_user_by_username_with_connection(&connection, username)?
            .ok_or_else(|| "invalid username or password".to_string())?;

        if !stored_user.profile.active {
            return Err("user has been disabled".to_string());
        }

        verify_password(password, &stored_user.password_hash)?;

        let token = Uuid::new_v4().to_string();
        let now = Utc::now().timestamp();
        let expires_at = now + SESSION_TTL_SECONDS;
        connection
            .execute(
                "INSERT INTO sessions (id, user_id, token_hash, created_at, expires_at) VALUES (?1, ?2, ?3, ?4, ?5)",
                params![
                    Uuid::new_v4().to_string(),
                    stored_user.profile.id,
                    hash_token(&token),
                    now,
                    expires_at
                ],
            )
            .map_err(|error| format!("failed to create session: {error}"))?;

        Ok(AuthSession {
            token,
            user: stored_user.profile,
        })
    }

    pub fn current_user(&self, token: &str) -> Result<Option<UserProfile>, String> {
        let connection = self.open()?;
        self.cleanup_expired_sessions_with_connection(&connection)?;

        let user = connection
            .prepare(
                "
                SELECT u.id, u.name, u.username, u.role, u.active, u.created_at, u.updated_at
                FROM sessions s
                INNER JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?1 AND s.expires_at > ?2
                ",
            )
            .map_err(|error| format!("failed to prepare session lookup: {error}"))?
            .query_row(params![hash_token(token), Utc::now().timestamp()], map_user_profile)
            .optional()
            .map_err(|error| format!("failed to query session: {error}"))?;

        Ok(user.filter(|profile| profile.active))
    }

    pub fn revoke_session(&self, token: &str) -> Result<(), String> {
        let connection = self.open()?;
        connection
            .execute("DELETE FROM sessions WHERE token_hash = ?1", params![hash_token(token)])
            .map_err(|error| format!("failed to revoke session: {error}"))?;
        Ok(())
    }

    pub fn list_users(&self) -> Result<Vec<UserProfile>, String> {
        let connection = self.open()?;
        let mut statement = connection
            .prepare(
                "
                SELECT id, name, username, role, active, created_at, updated_at
                FROM users
                ORDER BY created_at DESC, username ASC
                ",
            )
            .map_err(|error| format!("failed to prepare user list query: {error}"))?;

        let rows = statement
            .query_map([], map_user_profile)
            .map_err(|error| format!("failed to query users: {error}"))?;

        let mut users = Vec::new();
        for row in rows {
            users.push(row.map_err(|error| format!("failed to read user row: {error}"))?);
        }
        Ok(users)
    }

    pub fn create_user(&self, name: String, username: String, password: String, role: UserRole) -> Result<UserProfile, String> {
        validate_name(&name)?;
        validate_username(&username)?;
        validate_password(&password)?;

        let connection = self.open()?;
        let now = Utc::now();
        let profile = UserProfile {
            id: Uuid::new_v4().to_string(),
            name: name.trim().to_string(),
            username: username.trim().to_string(),
            role,
            active: true,
            created_at: now,
            updated_at: now,
        };
        let password_hash = hash_password(&password)?;

        connection
            .execute(
                "
                INSERT INTO users (id, name, username, password_hash, role, active, created_at, updated_at)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)
                ",
                params![
                    profile.id,
                    profile.name,
                    profile.username,
                    password_hash,
                    profile.role.as_str(),
                    if profile.active { 1 } else { 0 },
                    profile.created_at.to_rfc3339(),
                    profile.updated_at.to_rfc3339()
                ],
            )
            .map_err(map_sqlite_error)?;

        Ok(profile)
    }

    pub fn reset_password(&self, user_id: &str, password: &str) -> Result<(), String> {
        validate_password(password)?;
        let connection = self.open()?;
        let updated_at = Utc::now().to_rfc3339();
        let affected = connection
            .execute(
                "UPDATE users SET password_hash = ?1, updated_at = ?2 WHERE id = ?3",
                params![hash_password(password)?, updated_at, user_id],
            )
            .map_err(|error| format!("failed to reset password: {error}"))?;
        if affected == 0 {
            return Err("user not found".to_string());
        }

        connection
            .execute("DELETE FROM sessions WHERE user_id = ?1", params![user_id])
            .map_err(|error| format!("failed to revoke existing sessions: {error}"))?;
        Ok(())
    }

    pub fn set_user_active(&self, user_id: &str, active: bool) -> Result<(), String> {
        let connection = self.open()?;
        let updated_at = Utc::now().to_rfc3339();
        let affected = connection
            .execute(
                "UPDATE users SET active = ?1, updated_at = ?2 WHERE id = ?3",
                params![if active { 1 } else { 0 }, updated_at, user_id],
            )
            .map_err(|error| format!("failed to update user status: {error}"))?;
        if affected == 0 {
            return Err("user not found".to_string());
        }

        if !active {
            connection
                .execute("DELETE FROM sessions WHERE user_id = ?1", params![user_id])
                .map_err(|error| format!("failed to revoke sessions for disabled user: {error}"))?;
        }
        Ok(())
    }

    fn open(&self) -> Result<Connection, String> {
        let connection = Connection::open(&self.db_path).map_err(|error| format!("failed to open auth store: {error}"))?;
        connection
            .execute_batch("PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;")
            .map_err(|error| format!("failed to configure auth store: {error}"))?;
        Ok(connection)
    }

    fn cleanup_expired_sessions_with_connection(&self, connection: &Connection) -> Result<(), String> {
        connection
            .execute("DELETE FROM sessions WHERE expires_at <= ?1", params![Utc::now().timestamp()])
            .map_err(|error| format!("failed to cleanup expired sessions: {error}"))?;
        Ok(())
    }

    fn ensure_bootstrap_admin_with_connection(&self, connection: &Connection) -> Result<(), String> {
        let user_count: i64 = connection
            .query_row("SELECT COUNT(*) FROM users", [], |row| row.get(0))
            .map_err(|error| format!("failed to count users: {error}"))?;

        if user_count > 0 {
            return Ok(());
        }

        let name = std::env::var("AUTO_PROMPT_ADMIN_NAME").unwrap_or_else(|_| DEFAULT_ADMIN_NAME.to_string());
        let username = std::env::var("AUTO_PROMPT_ADMIN_USERNAME").unwrap_or_else(|_| DEFAULT_ADMIN_USERNAME.to_string());
        let password = std::env::var("AUTO_PROMPT_ADMIN_PASSWORD").unwrap_or_else(|_| DEFAULT_ADMIN_PASSWORD.to_string());

        let now = Utc::now();
        connection
            .execute(
                "
                INSERT INTO users (id, name, username, password_hash, role, active, created_at, updated_at)
                VALUES (?1, ?2, ?3, ?4, 'admin', 1, ?5, ?6)
                ",
                params![
                    Uuid::new_v4().to_string(),
                    name.trim(),
                    username.trim(),
                    hash_password(&password)?,
                    now.to_rfc3339(),
                    now.to_rfc3339()
                ],
            )
            .map_err(|error| format!("failed to create bootstrap admin: {error}"))?;

        println!(
            "bootstrap admin created: username={} password={}",
            username.trim(),
            password
        );
        Ok(())
    }

    fn find_user_by_username_with_connection(&self, connection: &Connection, username: &str) -> Result<Option<StoredUser>, String> {
        let mut statement = connection
            .prepare(
                "
                SELECT id, name, username, role, active, created_at, updated_at, password_hash
                FROM users
                WHERE username = ?1
                ",
            )
            .map_err(|error| format!("failed to prepare user lookup: {error}"))?;

        statement
            .query_row(params![username.trim()], |row| {
                Ok(StoredUser {
                    profile: map_user_profile(row)?,
                    password_hash: row.get(7)?,
                })
            })
            .optional()
            .map_err(|error| format!("failed to query user: {error}"))
    }
}

fn map_user_profile(row: &rusqlite::Row<'_>) -> rusqlite::Result<UserProfile> {
    Ok(UserProfile {
        id: row.get(0)?,
        name: row.get(1)?,
        username: row.get(2)?,
        role: UserRole::from_str(&row.get::<_, String>(3)?)
            .map_err(|error| rusqlite::Error::FromSqlConversionFailure(3, rusqlite::types::Type::Text, Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, error))))?,
        active: row.get::<_, i64>(4)? != 0,
        created_at: parse_datetime(&row.get::<_, String>(5)?)
            .map_err(|error| rusqlite::Error::FromSqlConversionFailure(5, rusqlite::types::Type::Text, Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, error))))?,
        updated_at: parse_datetime(&row.get::<_, String>(6)?)
            .map_err(|error| rusqlite::Error::FromSqlConversionFailure(6, rusqlite::types::Type::Text, Box::new(std::io::Error::new(std::io::ErrorKind::InvalidData, error))))?,
    })
}

fn parse_datetime(value: &str) -> Result<DateTime<Utc>, String> {
    chrono::DateTime::parse_from_rfc3339(value)
        .map(|dt| dt.with_timezone(&Utc))
        .map_err(|error| format!("failed to parse timestamp: {error}"))
}

fn hash_password(password: &str) -> Result<String, String> {
    let salt = SaltString::generate(&mut OsRng);
    Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map(|hash| hash.to_string())
        .map_err(|error| format!("failed to hash password: {error}"))
}

fn verify_password(password: &str, password_hash: &str) -> Result<(), String> {
    let parsed = PasswordHash::new(password_hash).map_err(|error| format!("failed to parse password hash: {error}"))?;
    Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .map_err(|_| "invalid username or password".to_string())
}

fn hash_token(token: &str) -> String {
    format!("{:x}", Sha256::digest(token.as_bytes()))
}

fn validate_name(name: &str) -> Result<(), String> {
    if name.trim().is_empty() {
        return Err("name cannot be empty".to_string());
    }
    Ok(())
}

fn validate_username(username: &str) -> Result<(), String> {
    let trimmed = username.trim();
    if trimmed.len() < 3 {
        return Err("username must be at least 3 characters".to_string());
    }
    if !trimmed
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '_' | '-' | '.'))
    {
        return Err("username may only contain letters, numbers, _, -, or .".to_string());
    }
    Ok(())
}

fn validate_password(password: &str) -> Result<(), String> {
    if password.len() < 6 {
        return Err("password must be at least 6 characters".to_string());
    }
    Ok(())
}

fn map_sqlite_error(error: rusqlite::Error) -> String {
    let message = error.to_string();
    if message.contains("UNIQUE constraint failed: users.username") {
        "username already exists".to_string()
    } else {
        format!("database error: {message}")
    }
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use uuid::Uuid;

    use super::{AuthStore, UserRole};

    fn temp_db_path(test_name: &str) -> PathBuf {
        std::env::temp_dir().join(format!("auto-prompt-auth-tests-{test_name}-{}.db", Uuid::new_v4()))
    }

    #[test]
    fn bootstraps_admin_and_authenticates() {
        let db_path = temp_db_path("bootstrap");
        let store = AuthStore::new(db_path.clone());
        store.initialize().unwrap();

        let users = store.list_users().unwrap();
        assert_eq!(users.len(), 1);
        assert!(users[0].role.is_admin());

        let session = store.authenticate("admin", "admin123456").unwrap();
        let current = store.current_user(&session.token).unwrap().unwrap();
        assert_eq!(current.username, "admin");

        let _ = std::fs::remove_file(db_path);
    }

    #[test]
    fn creates_users_and_resets_passwords() {
        let db_path = temp_db_path("create-user");
        let store = AuthStore::new(db_path.clone());
        store.initialize().unwrap();

        let user = store
            .create_user("Alice".to_string(), "alice".to_string(), "secret123".to_string(), UserRole::User)
            .unwrap();
        assert_eq!(user.username, "alice");

        assert!(store.authenticate("alice", "wrong").is_err());
        assert!(store.authenticate("alice", "secret123").is_ok());

        store.reset_password(&user.id, "changed456").unwrap();
        assert!(store.authenticate("alice", "secret123").is_err());
        assert!(store.authenticate("alice", "changed456").is_ok());

        let _ = std::fs::remove_file(db_path);
    }

    #[test]
    fn disabling_user_revokes_access() {
        let db_path = temp_db_path("disable-user");
        let store = AuthStore::new(db_path.clone());
        store.initialize().unwrap();

        let user = store
            .create_user("Bob".to_string(), "bob".to_string(), "secret123".to_string(), UserRole::User)
            .unwrap();
        let session = store.authenticate("bob", "secret123").unwrap();
        store.set_user_active(&user.id, false).unwrap();

        assert!(store.current_user(&session.token).unwrap().is_none());
        assert!(store.authenticate("bob", "secret123").is_err());

        let _ = std::fs::remove_file(db_path);
    }
}
