USE multiple_agent_finance;

CREATE TABLE IF NOT EXISTS financial_quarterly_metrics (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  statement_type VARCHAR(32) NOT NULL,
  fiscal_date DATE NOT NULL,
  metric_name VARCHAR(255) NOT NULL,
  metric_value DECIMAL(30,6) NULL,
  raw_value VARCHAR(255) NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'yfinance',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_fqm_run (run_id),
  KEY idx_fqm_ticker_date (ticker, fiscal_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS news_daily_top_items (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  news_date DATE NOT NULL,
  rank_no INT NOT NULL,
  title VARCHAR(1024) NOT NULL,
  publisher VARCHAR(255) NULL,
  link VARCHAR(2048) NULL,
  published_at DATETIME NULL,
  source VARCHAR(64) NOT NULL,
  query_text VARCHAR(1024) NULL,
  raw_payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ndti_run (run_id),
  KEY idx_ndti_ticker_date (ticker, news_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
