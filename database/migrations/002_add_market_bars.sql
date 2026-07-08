USE multiple_agent_finance;

CREATE TABLE IF NOT EXISTS market_bars (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ticker VARCHAR(32) NOT NULL,
  bar_date DATE NOT NULL,
  open_price DECIMAL(20,6) NULL,
  high_price DECIMAL(20,6) NULL,
  low_price DECIMAL(20,6) NULL,
  close_price DECIMAL(20,6) NULL,
  volume BIGINT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'yfinance',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_market_bars_ticker_date_source (ticker, bar_date, source),
  KEY idx_market_bars_ticker_date (ticker, bar_date),
  CONSTRAINT fk_market_bars_symbol
    FOREIGN KEY (ticker) REFERENCES symbols (ticker)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB;
