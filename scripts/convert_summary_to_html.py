from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "docs" / "finrl_tensortrade_paper_summary.md"
target = (
    Path.home()
    / ".codex"
    / "visualizations"
    / "2026"
    / "07"
    / "13"
    / "019f5926-8325-70d1-99a9-8a35468e3e24"
    / "finrl_tensortrade_paper_summary.html"
)

body = markdown.markdown(
    source.read_text(encoding="utf-8"),
    extensions=["tables", "fenced_code", "toc"],
)

css = """
body {
  font-family: "Microsoft YaHei", SimSun, Arial, sans-serif;
  line-height: 1.65;
  color: #1f2933;
  margin: 42px auto;
  max-width: 920px;
  font-size: 14px;
}
h1 {
  font-size: 28px;
  border-bottom: 2px solid #222;
  padding-bottom: 10px;
}
h2 {
  font-size: 22px;
  margin-top: 32px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 6px;
}
h3 {
  font-size: 17px;
  margin-top: 24px;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  font-size: 12px;
}
th,
td {
  border: 1px solid #ccc;
  padding: 7px;
  vertical-align: top;
}
th {
  background: #f2f4f7;
}
code {
  font-family: Consolas, monospace;
  background: #f4f4f4;
  padding: 1px 4px;
  border-radius: 3px;
}
pre {
  background: #f7f7f7;
  padding: 12px;
  overflow: auto;
}
a {
  color: #0b63ce;
  text-decoration: none;
}
@page {
  size: A4;
  margin: 20mm 17mm;
}
"""

target.write_text(
    f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>FinRL 系列论文与 TensorTrade 代码总结</title>
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
""",
    encoding="utf-8",
)

print(target)
