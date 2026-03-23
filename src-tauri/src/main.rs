// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use commands::{cases, classify, config, env_check, factor_json, fs, generate, llm_log, review_rule, skills_manager};

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // Generate commands
            generate::read_factors,
            generate::get_materials,
            generate::generate_prompt,
            generate::verify_extraction,
            generate::save_prompt_file,
            // Classify commands
            classify::get_material_categories,
            classify::get_pending_files,
            classify::classify_materials,
            classify::test_classify_prompt,
            classify::open_classified_dir,
            // Case commands
            cases::load_case_library,
            cases::search_cases,
            cases::import_cases,
            cases::import_case_library_json,
            cases::import_cases_from_txt,
            cases::delete_case,
            // FS commands
            fs::read_directory,
            fs::read_file,
            fs::write_file,
            fs::select_directory,
            fs::select_file,
            fs::select_files,
            // Factor JSON commands
            factor_json::generate_factor_json,
            factor_json::read_json_file,
            factor_json::open_in_finder,
            // Skills manager commands
            skills_manager::list_skills,
            skills_manager::import_skill_files,
            // Config commands
            config::load_settings,
            config::save_settings,
            config::get_default_god_prompts,
            config::test_api_key,
            // Review rule commands
            review_rule::generate_review_rule,
            review_rule::write_json_file,
            review_rule::regenerate_keypoint,
            // LLM log commands
            llm_log::get_llm_logs,
            llm_log::clear_llm_logs,
            // Env check commands
            env_check::check_environment,
            env_check::install_packages,
            env_check::install_python,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
