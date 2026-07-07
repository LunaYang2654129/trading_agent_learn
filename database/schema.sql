-- MySQL schema for the LangGraph multi-agent finance system.
-- Target: MySQL 8.0+

CREATE DATABASE IF NOT EXISTS multiple_agent_finance
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'maf_app'@'localhost'
  IDENTIFIED BY 'maf_password_change_me';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
  ON multiple_agent_finance.*
  TO 'maf_app'@'localhost';

USE multiple_agent_finance;

CREATE TABLE IF NOT EXISTS symbols (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ticker VARCHAR(32) NOT NULL,
  exchange VARCHAR(32) NULL,
  company_name VARCHAR(255) NULL,
  sector VARCHAR(128) NULL,
  industry VARCHAR(128) NULL,
  website VARCHAR(512) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_symbols_ticker (ticker)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS analysis_runs (
  id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  user_request TEXT NOT NULL,
  as_of_date DATE NULL,
  status ENUM('started', 'completed', 'failed') NOT NULL DEFAULT 'completed',
  confidence_score DECIMAL(6,4) NULL,
  confidence_threshold DECIMAL(6,4) NULL,
  max_retries INT NOT NULL DEFAULT 1,
  retry_count INT NOT NULL DEFAULT 0,
  rating VARCHAR(64) NULL,
  risk_score TINYINT UNSIGNED NULL,
  risk_level VARCHAR(32) NULL,
  final_report_path VARCHAR(1024) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_analysis_runs_ticker_date (ticker, as_of_date),
  KEY idx_analysis_runs_created_at (created_at),
  CONSTRAINT fk_analysis_runs_symbol
    FOREIGN KEY (ticker) REFERENCES symbols (ticker)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS agent_outputs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  agent_name VARCHAR(64) NOT NULL,
  output_type VARCHAR(64) NOT NULL,
  payload JSON NOT NULL,
  warnings JSON NULL,
  sources JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_agent_outputs_run_agent (run_id, agent_name),
  CONSTRAINT fk_agent_outputs_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS market_snapshots (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  price DECIMAL(20,6) NULL,
  volume BIGINT NULL,
  ma20 DECIMAL(20,6) NULL,
  ma60 DECIMAL(20,6) NULL,
  return_20d DECIMAL(12,8) NULL,
  volatility_20d DECIMAL(12,8) NULL,
  trend VARCHAR(32) NULL,
  indicators JSON NULL,
  sources JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_market_snapshots_ticker_created (ticker, created_at),
  CONSTRAINT fk_market_snapshots_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE,
  CONSTRAINT fk_market_snapshots_symbol
    FOREIGN KEY (ticker) REFERENCES symbols (ticker)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS company_profiles (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  company_name VARCHAR(255) NULL,
  sector VARCHAR(128) NULL,
  industry VARCHAR(128) NULL,
  market_cap DECIMAL(24,2) NULL,
  business_summary MEDIUMTEXT NULL,
  main_products JSON NULL,
  key_risks JSON NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_company_profiles_ticker_created (ticker, created_at),
  CONSTRAINT fk_company_profiles_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS financial_metrics (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  revenue DECIMAL(24,2) NULL,
  net_income DECIMAL(24,2) NULL,
  roe DECIMAL(12,8) NULL,
  debt_to_asset DECIMAL(12,8) NULL,
  gross_margin DECIMAL(12,8) NULL,
  operating_cashflow DECIMAL(24,2) NULL,
  cash_flow_quality DECIMAL(12,8) NULL,
  financial_risks JSON NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_financial_metrics_ticker_created (ticker, created_at),
  CONSTRAINT fk_financial_metrics_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS news_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  title VARCHAR(1024) NOT NULL,
  publisher VARCHAR(255) NULL,
  link VARCHAR(2048) NULL,
  published_at DATETIME NULL,
  sentiment VARCHAR(32) NULL,
  labels JSON NULL,
  raw_payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_news_items_ticker_published (ticker, published_at),
  CONSTRAINT fk_news_items_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS risk_assessments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  risk_score TINYINT UNSIGNED NULL,
  risk_level VARCHAR(32) NULL,
  risk_points JSON NULL,
  warnings JSON NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_risk_assessments_ticker_score (ticker, risk_score),
  CONSTRAINT fk_risk_assessments_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS decision_summaries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  rating VARCHAR(64) NULL,
  confidence DECIMAL(6,4) NULL,
  risk_score TINYINT UNSIGNED NULL,
  supporting_points JSON NULL,
  risk_points JSON NULL,
  warnings JSON NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_decision_summaries_run (run_id),
  CONSTRAINT fk_decision_summaries_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reflection_reviews (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  passed BOOLEAN NOT NULL DEFAULT FALSE,
  completeness_score DECIMAL(6,4) NULL,
  logic_score DECIMAL(6,4) NULL,
  risk_coverage_score DECIMAL(6,4) NULL,
  missing_items JSON NULL,
  retry_tasks JSON NULL,
  review_comment TEXT NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_reflection_reviews_run (run_id),
  CONSTRAINT fk_reflection_reviews_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS final_reports (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  report_path VARCHAR(1024) NULL,
  report_markdown MEDIUMTEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_final_reports_run (run_id),
  CONSTRAINT fk_final_reports_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  agent_name VARCHAR(64) NULL,
  message VARCHAR(512) NOT NULL,
  payload JSON NULL,
  event_time DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_audit_events_run_agent (run_id, agent_name),
  CONSTRAINT fk_audit_events_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS shared_memory_entries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NULL,
  agent_name VARCHAR(64) NULL,
  memory_key VARCHAR(255) NOT NULL,
  memory_value JSON NOT NULL,
  importance DECIMAL(6,4) NOT NULL DEFAULT 0.5000,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_shared_memory_key (memory_key),
  CONSTRAINT fk_shared_memory_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS knowledge_documents (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_name VARCHAR(255) NOT NULL,
  source_type VARCHAR(64) NOT NULL,
  title VARCHAR(512) NULL,
  uri VARCHAR(1024) NULL,
  content_hash CHAR(64) NULL,
  metadata JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_knowledge_documents_hash (content_hash),
  KEY idx_knowledge_documents_source (source_type, source_name)
) ENGINE=InnoDB;
