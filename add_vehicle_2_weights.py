# just to update the current master_cases.xlsx file.

from pathlib import Path
import pandas as pd

files = sorted(Path("ciren_database/CrashExports").glob("CrashExport-*.xlsx"))
master = pd.read_excel("ciren_database/master_cases.xlsx")
# ensure cirenid is the index so we can assign by loc
master.set_index("cirenid", inplace=True)

for file in files:
    # get ciren_id from file
    df_adm = pd.read_excel(file, sheet_name="ADMISSIONS")
    ciren_id = int(df_adm["CIRENID"].iloc[0])

    # get weight of second vehicle from file
    df_gv = pd.read_excel(file, sheet_name="GV")
    row = df_gv[df_gv["VEHNO"] == 2]
    if row.empty:
        continue
    weight = round(float(row["CURBWT"].iloc[0]), 1)

    # store weight in new column in master file
    if ciren_id in master.index:
        master.loc[ciren_id, "vehicle2_weight"] = weight

# write updated master to a new file
master.reset_index().to_excel("ciren_database/master_cases_with_weights.xlsx", index=False)
    