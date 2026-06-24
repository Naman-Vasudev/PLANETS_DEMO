import os
import sys

# Add to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import server
import report_generator

# Define target candidates to run and generate PDFs for
targets = [
    {"id": "261108232", "desc": "TIC 261108232 (TESS Confirmed Planet)"},
    {"id": "10797460", "desc": "KIC 10797460 (Kepler Confirmed Planet)"},
    {"id": "294329732", "desc": "TIC 294329732 (TESS Super-Earth with override)", "period": 9.8, "t0": 1320.0, "duration": 2.5}
]

results_list = []

for t in targets:
    print(f"\n==================================================")
    print(f"Processing: {t['desc']}")
    print(f"==================================================")
    
    if "period" in t:
        result = server.run_pipeline(
            t["id"],
            period_override=t["period"],
            t0_override=t["t0"],
            duration_override=t["duration"]
        )
    else:
        result = server.run_pipeline(t["id"])
        
    if "error" in result:
        print(f"Error executing pipeline for {t['id']}: {result['error']}")
        continue
        
    results_list.append(result)
    
    try:
        pdf_bytes = report_generator.generate_pdf_report(result)
        out_name = f"Research_Report_TIC_{t['id']}.pdf" if len(t['id']) >= 9 else f"Research_Report_KIC_{t['id']}.pdf"
        out_path = os.path.join(r"n:\PLANETS", out_name)
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"✅ Successfully saved report to: {out_path}")
    except Exception as pdf_err:
        print(f"❌ Error generating PDF: {pdf_err}")

print(f"\n==================================================")
print(f"Compiling Consolidated 3-Page Scientific Report...")
print(f"==================================================")
try:
    consolidated_pdf_bytes = report_generator.generate_consolidated_pdf_report(results_list)
    consolidated_path = os.path.join(r"n:\PLANETS", "Consolidated_Research_Report.pdf")
    with open(consolidated_path, "wb") as f:
        f.write(consolidated_pdf_bytes)
    print(f"✅ Successfully saved consolidated report to: {consolidated_path}")
except Exception as con_err:
    print(f"❌ Error generating consolidated PDF: {con_err}")

print("\nDone. All reports generated.")
