USE multiple_agent_finance;

CREATE TABLE IF NOT EXISTS technical_indicators (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_id CHAR(36) NOT NULL,
  ticker VARCHAR(32) NOT NULL,
  trend VARCHAR(32) NULL,
  volume_signal VARCHAR(32) NULL,
  macd_signal VARCHAR(32) NULL,
  rsi_signal VARCHAR(32) NULL,
  valuation_pe DECIMAL(18,6) NULL,
  valuation_pb DECIMAL(18,6) NULL,
  support DECIMAL(20,6) NULL,
  resistance DECIMAL(20,6) NULL,
  indicators JSON NULL,
  technical_risks JSON NULL,
  warnings JSON NULL,
  raw_payload JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_technical_indicators_ticker_created (ticker, created_at),
  CONSTRAINT fk_technical_indicators_run
    FOREIGN KEY (run_id) REFERENCES analysis_runs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB;
