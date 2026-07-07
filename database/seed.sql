USE multiple_agent_finance;

INSERT INTO symbols (ticker, company_name, sector, industry)
VALUES
  ('AAPL', 'Apple Inc.', 'Technology', 'Consumer Electronics'),
  ('MSFT', 'Microsoft Corporation', 'Technology', 'Software'),
  ('NVDA', 'NVIDIA Corporation', 'Technology', 'Semiconductors')
ON DUPLICATE KEY UPDATE
  company_name = VALUES(company_name),
  sector = VALUES(sector),
  industry = VALUES(industry);
