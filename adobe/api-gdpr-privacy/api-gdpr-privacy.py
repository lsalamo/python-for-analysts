import requests
import pandas as pd
import os
import shutil
import sys
from datetime import datetime
from datetime import timedelta

# =============================================================================
# VARIABLES
# =============================================================================
TOKEN = "eyJhbGciOiJSUzI1NiIsIng1dSI6Imltc19uYTEta2V5LTEuY2VyIn0.eyJpZCI6IjE2MjMwNTY4MTI3NjJfNWQ1YjNiOGUtZjM0OC00NWFhLThmMzItZGJkMmYwNjM3ODY4X3VlMSIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiI1ZTlmZDU1ZmE5MmM0YTBhODJiM2YyYTc0YzA4OGU2MCIsInVzZXJfaWQiOiJBRDRBN0ExRDYwODhGOUY0MEE0OTVDNjhAdGVjaGFjY3QuYWRvYmUuY29tIiwiYXMiOiJpbXMtbmExIiwiYWFfaWQiOiJBRDRBN0ExRDYwODhGOUY0MEE0OTVDNjhAdGVjaGFjY3QuYWRvYmUuY29tIiwiZmciOiJWUUJLRjdZN0ZMUDU1WFVDQ01aTFJIUUFBND09PT09PSIsIm1vaSI6IjdmYjc1YTZiIiwiZXhwaXJlc19pbiI6Ijg2NDAwMDAwIiwic2NvcGUiOiJvcGVuaWQsQWRvYmVJRCxyZWFkX29yZ2FuaXphdGlvbnMsYWRkaXRpb25hbF9pbmZvLnByb2plY3RlZFByb2R1Y3RDb250ZXh0IiwiY3JlYXRlZF9hdCI6IjE2MjMwNTY4MTI3NjIifQ.Aqa_kCCUDDZy0gWTysug6ggCkXgOohNSyz7B4FsppudqY0uIGLFtjLtbal_S_k6EaMBUB8vp1Xy7UXOsd_z-EOYhu6tO9ehEOTQse9r0Et-CyVYO7j5C45g0YSaDQxCPQZtFHCrEi8hd63HPYAUFuBBqcuoM1blUKX0lxlqBNNcNbvWBV1TJQXCzD5ltKWjmt_2i8PK0VYMBw6zUrC20WKGJ_DPT0gvcaIrwg_BYO3VGxKbuWU-C_jsj3QBnZNSfh6m6z0S8TIWZyOy_gVAEz54wEk_fuMtJX5G9RIorgoUhneRsFxvgIIQUOCQVELcEEqYN-nWkEqdcsgqcMb88wA"
FROM_DATE = "2021-05-24"
TO_DATE = "2021-05-30"
DIR_PARENT = "/Users/luis.salamo/Documents/github enterprise/python-training/adobe/api-gdpr-privacy"
DIR_EXPORT = 'export' 

# =============================================================================
# REQUEST
# =============================================================================
url = "https://platform.adobe.io/data/core/privacy/jobs?regulation=gdpr&size=100&page={{page}}&status=&fromDate={{from_date}}&toDate={{to_date}}&filterDate="
url = url.replace("{{from_date}}", FROM_DATE).replace("{{to_date}}", TO_DATE)
payload = {}
headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer ' + TOKEN,
  'x-api-key': '5e9fd55fa92c4a0a82b3f2a74c088e60',
  'x-gw-ims-org-id': '05FF6243578784B37F000101@AdobeOrg',
  'x-sandbox-name': 'prod'
}
response = requests.request("GET", url.replace("{{page}}", "1"), headers=headers, data=payload)

# =============================================================================
#   REQUEST
# =============================================================================

df = pd.DataFrame();
if response.status_code != 200:
    sys.exit("ERROR " + str(response.status_code) + " > " + response.text) 
else:
    print("page 1 loaded")
    response = response.json()
    total_records = response['totalRecords']
    if total_records > 0:
        df = df.append(pd.DataFrame.from_dict(response['jobDetails']))
        iterator = (total_records // 100) + 2
        for i in range(2, iterator):
            print("page " + str(i) + " loaded")
            response = requests.request("GET", url.replace("{{page}}", str(i)), headers=headers, data=payload)
            response = response.json()
            df = df.append(pd.DataFrame.from_dict(response['jobDetails']))

# =============================================================================
#   CAST
# =============================================================================

df['createdDate_datetime'] = pd.to_datetime(pd.to_datetime(df['createdDate']).dt.strftime('%Y-%m-%d %H:%M:%S'))
df['lastModifiedDate_datetime'] = pd.to_datetime(pd.to_datetime(df['lastModifiedDate']).dt.strftime('%Y-%m-%d %H:%M:%S'))
df["createdDate_datetime_ymd"] = df["createdDate_datetime"].dt.strftime('%Y-%m-%d')
df["diffDate"] = df["lastModifiedDate_datetime"] - df["createdDate_datetime"]

# =============================================================================
#   CLEAR
# =============================================================================

df_clean = df[df["userKey"].str.startswith("Analytics-") & df["userKey"].str.contains("sdrn:")]

# =============================================================================
#   RESULT
# =============================================================================

df_summary_by_day = df_clean.groupby(["createdDate_datetime_ymd", "action", "status"]).agg(
    count = pd.NamedAgg(column="jobId", aggfunc="count"),
    min = pd.NamedAgg(column="diffDate", aggfunc="min"),
    max = pd.NamedAgg(column="diffDate", aggfunc="max"),
    mean = pd.NamedAgg(column="diffDate", aggfunc=lambda x: x.mean())
)

def get_summary():
    count = df_clean.shape[0]
    count_delete = df_clean[df_clean["action"] == "delete"].shape[0]
    count_access = df_clean[df_clean["action"] == "access"].shape[0]
    date_from = datetime.strptime(FROM_DATE, '%Y-%m-%d').date()
    date_to = datetime.strptime(TO_DATE, '%Y-%m-%d').date()
    date_diff = (date_to - date_from).days + 1
    data = {
        'count': count,
        'count_delete': count_delete,
        'count_access': count_access,
        '%_count_delete': round(count_delete / count * 100, 2),
        '%_count_access': round(count_access / count * 100, 2),
        'date_from': date_from,
        'date_to': date_to,
        'date_diff': (date_to - date_from).days + 1,
        'count / day': round(count / date_diff),
        'time_min_delete': df_clean[(df_clean["action"] == "delete") & (df_clean["status"] == "complete")]["diffDate"].min().to_pytimedelta(),
        'time_min_access': df_clean[(df_clean["action"] == "access") & (df_clean["status"] == "complete")]["diffDate"].min().to_pytimedelta(),
        'time_max_delete': df_clean[(df_clean["action"] == "delete") & (df_clean["status"] == "complete")]["diffDate"].max().to_pytimedelta(),
        'time_max_access': df_clean[(df_clean["action"] == "access") & (df_clean["status"] == "complete")]["diffDate"].max().to_pytimedelta(),
        'time_mean_delete': df_clean[(df_clean["action"] == "delete") & (df_clean["status"] == "complete")]["diffDate"].mean().to_pytimedelta(),
        'time_mean_access': df_clean[(df_clean["action"] == "access") & (df_clean["status"] == "complete")]["diffDate"].mean().to_pytimedelta()
    }
    data["time_mean_delete"] = data["time_mean_delete"] - timedelta(microseconds=data["time_mean_delete"].microseconds)
    data["time_mean_access"] = data["time_mean_access"] - timedelta(microseconds=data["time_mean_access"].microseconds)
    return data

result = { 
    'total_records': df_clean.shape[0], 
    'df': df,
    'df_clean': df_clean,
    'df_summary': get_summary(),
    'df_summary_by_day': df_summary_by_day
}

# =============================================================================
#   EXPORT CSV
# =============================================================================


df_summary = pd.DataFrame.from_dict(list(result["df_summary"].items()))
df_summary.rename(columns={0:'Key', 1:'Value'}, inplace = True)
df_summary.set_index('Key', inplace = True)

dir = os.path.join(DIR_PARENT, DIR_EXPORT)
if os.path.isdir(dir):
    shutil.rmtree(dir)
os.makedirs(dir)
result['df_summary_by_day'].to_csv(dir + "/data_summary_by_day.csv")
result['df_summary'].to_csv(dir + "/data_summary.csv")

a = result['df_clean'][result['df_clean']['userKey'].str.contains("40558615524")]


