import requests
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from base64 import b64decode
import datetime
import numpy as np


def convert_date(date_num): 
    parsed_date = datetime.datetime.fromtimestamp(int(date_num / 1000)) + datetime.timedelta(days=1)
    return parsed_date.strftime("%Y-%m-%d")


def parse_data(data_location, level_type):
    dates = []
    values = []

    for i, _ in enumerate(data_location):
        raw_date = data_location[i]['C'][0]
        parsed_date = convert_date(raw_date)
        dates.append(parsed_date)
        try:
            values.append(data_location[i]['C'][1])
        except IndexError:
            values.append(values[i - 1])

    df = pd.DataFrame({'Date': dates,
                       'Level': [f'{level_type}'] * len(dates),
                       'values': values})

    complete_dates = pd.period_range('04-01-2020', df['Date'].max())
    complete_dates = complete_dates.strftime('%Y-%m-%d').to_series().to_list()

    # fill missing dates
    df = df.set_index('Date')
    df = df.reindex(complete_dates, fill_value=np.nan)
    df.loc[df['Level'].isna(), 'Level'] = level_type
    df['Date'] = df.index
    df = df.reset_index(drop=True)
    df = df[['Date', 'Level', 'values']]

    # fix N/As: only real NA date is 5/22 for certain counties
    # other N/As are presented as repeat values of previous day value on the site
    
    df.loc[(df['Date'] == '2020-05-22') & (df['values'].isna()), 'values'] = 'N/A'
    df.fillna(method='ffill', inplace=True)

    return df


def get_tokens(page_url):
    soup = BeautifulSoup(requests.get(page_url).content, 'html.parser')
    page_text = str(soup)

    encoded_resource = re.search('(r=)(.*)(\&)', page_url).group(2)
    resource_key = json.loads(b64decode(encoded_resource))['k']
    request_id = re.search("var requestId = \\'(.*?)\\';", page_text).group(1)
    activity_id = re.search("var telemetrySessionId =  \\'(.*?)\\';", page_text).group(1)

    return resource_key, activity_id, request_id


# old url
# page_url = 'https://app.powerbi.com/view?r=eyJrIjoiOWU1ZTQ0MmQtYjEzNi00N2FlLTg0OTYtMjkzYjU4OWEwMzY5IiwidCI6ImI3MjgwODdjLTgwZTgtNGQzMS04YjZmLTdlMGUzYmUxMGUwOCIsImMiOjN9&pageName=ReportSectionc4498c097c625609dc1d'
page_url = 'https://app.powerbi.com/view?r=eyJrIjoiNDBlNmRlNzEtYWE2Ny00ZmM3LWEwY2YtMDE5NzliZTE5Y2ZjIiwidCI6ImI3MjgwODdjLTgwZTgtNGQzMS04YjZmLTdlMGUzYmUxMGUwOCIsImMiOjN9&pageName=ReportSectiondb4e38c4c14ac93c1c08'
resource_key, activity_id, request_id = get_tokens(page_url)
headers = {
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Accept': 'application/json',
    'X-PowerBI-ResourceKey': resource_key,
    'ActivityId': activity_id,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66',
    'RequestId': request_id,
    'Origin': 'https://app.powerbi.com',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://app.powerbi.com/',
    'Accept-Language': 'en-US,en;q=0.9'}
params = (('preferReadOnlySession', 'true'))
query_url = 'https://wabi-us-north-central-api.analysis.windows.net/public/reports/querydata?synchronous=true'


def get_icu_data(county):
    # old payload
    # payload = {"version":"1.0.0","queries":[{"Query":{"Commands":[{"SemanticQueryDataShapeCommand":{"Query":{"Version":2,"From":[{"Name":"h","Entity":"Hospital_Info","Type":0},{"Name":"d","Entity":"Date","Type":0},{"Name":"s1","Entity":"SETRAC Measures","Type":0},{"Name":"t","Entity":"TSA_County","Type":0}],"Select":[{"Column":{"Expression":{"SourceRef":{"Source":"d"}},"Property":"Date"},"Name":"Date.Date"},{"Measure":{"Expression":{"SourceRef":{"Source":"s1"}},"Property":"Patients in Intensive Care Beds (Suspected + Confirmed)"},"Name":"SurvData.Patients in Intensive Care Beds (Suspected + Confirmed)"}],"Where":[{"Condition":{"Comparison":{"ComparisonKind":2,"Left":{"Column":{"Expression":{"SourceRef":{"Source":"d"}},"Property":"Date"}},"Right":{"Literal":{"Value":"datetime'2020-04-01T00:00:00'"}}}}},{"Condition":{"In":{"Expressions":[{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":"County"}}],"Values":[[{"Literal":{"Value":"'Harris'"}}]]}}},{"Condition":{"Not":{"Expression":{"Comparison":{"ComparisonKind":0,"Left":{"Column":{"Expression":{"SourceRef":{"Source":"h"}},"Property":"Hospital Name"}},"Right":{"Literal":{"Value":"null"}}}}}}}]},"Binding":{"Primary":{"Groupings":[{"Projections":[0,1]}]},"DataReduction":{"DataVolume":2,"Primary":{"BinnedLineSample":{}}},"Version":1}}}]},"QueryId":"","ApplicationContext":{"DatasetId":"92bf5cbe-7a49-4548-a0b0-82e6a1d9ed1d","Sources":[{"ReportId":"db2a8e7a-2dc2-4ccd-8f8d-7aa98f5d424b"}]}}],"cancelQueries":[],"modelId":12328350    }

    payload = {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [
                                        {
                                            "Name": "h",
                                            "Entity": "Hospital_Info",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "d",
                                            "Entity": "Date",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "s1",
                                            "Entity": "SETRAC Measures",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "t",
                                            "Entity": "TSA_County",
                                            "Type": 0
                                        }
                                    ],
                                    "Select": [
                                        {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {
                                                        "Source": "d"
                                                    }
                                                },
                                                "Property": "Date"
                                            },
                                            "Name": "Date.Date"
                                        },
                                        {
                                            "Measure": {
                                                "Expression": {
                                                    "SourceRef": {
                                                        "Source": "s1"
                                                    }
                                                },
                                                "Property": "Patients in Intensive Care Beds (Suspected + Confirmed)"
                                            },
                                            "Name": "SurvData.Patients in Intensive Care Beds (Suspected + Confirmed)"
                                        }
                                    ],
                                    "Where": [
                                        {
                                            "Condition": {
                                                "Comparison": {
                                                    "ComparisonKind": 2,
                                                    "Left": {
                                                        "Column": {
                                                            "Expression": {
                                                                "SourceRef": {
                                                                    "Source": "d"
                                                                }
                                                            },
                                                            "Property": "Date"
                                                        }
                                                    },
                                                    "Right": {
                                                        "Literal": {
                                                            "Value": "datetime'2020-04-01T00:00:00'"
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "In": {
                                                    "Expressions": [
                                                        {
                                                            "Column": {
                                                                "Expression": {
                                                                    "SourceRef": {
                                                                        "Source": "t"
                                                                    }
                                                                },
                                                                "Property": "County"
                                                            }
                                                        }
                                                    ],
                                                    "Values": [
                                                        [
                                                            {
                                                                "Literal": {
                                                                    "Value": f"'{county}'"
                                                                }
                                                            }
                                                        ]
                                                    ]
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "Not": {
                                                    "Expression": {
                                                        "Comparison": {
                                                            "ComparisonKind": 0,
                                                            "Left": {
                                                                "Column": {
                                                                    "Expression": {
                                                                        "SourceRef": {
                                                                            "Source": "h"
                                                                        }
                                                                    },
                                                                    "Property": "Hospital Name"
                                                                }
                                                            },
                                                            "Right": {
                                                                "Literal": {
                                                                    "Value": "null"
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                },
                                "Binding": {
                                    "Primary": {
                                        "Groupings": [
                                            {
                                                "Projections": [
                                                    0,
                                                    1
                                                ]
                                            }
                                        ]
                                    },
                                    "DataReduction": {
                                        "DataVolume": 2,
                                        "Primary": {
                                            "BinnedLineSample": {}
                                        }
                                    },
                                    "Version": 1
                                }
                            }
                        }
                    ]
                },
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": "d31709e8-3813-4fe6-9ed5-68720a203fa2",
                    "Sources": [
                        {
                            "ReportId": "7f7a5d35-838d-48ce-9db5-547dc585fdfd"
                        }
                    ]
                }
            }
        ],
        "cancelQueries": [],
        "modelId": 12388057
    }
    
    response = requests.post(query_url, json=payload, headers=headers).json()
    data = response['results'][0]['result']['data']['dsr']['DS'][0]['PH'][0]['DM0']
    df = parse_data(data, county)
    return df


def get_gen_data(county):
    # old payload
    # payload = {"version":"1.0.0","queries":[{"Query":{"Commands":[{"SemanticQueryDataShapeCommand":{"Query":{"Version":2,"From":[{"Name":"h","Entity":"Hospital_Info","Type":0},{"Name":"d","Entity":"Date","Type":0},{"Name":"s1","Entity":"SETRAC Measures","Type":0},{"Name":"t","Entity":"TSA_County","Type":0}],"Select":[{"Column":{"Expression":{"SourceRef":{"Source":"d"}},"Property":"Date"},"Name":"Date.Date"},{"Measure":{"Expression":{"SourceRef":{"Source":"s1"}},"Property":"Patients in General Beds (Suspected + Confirmed)"},"Name":"SurvData.Patients in General Beds (Suspected + Confirmed)"}],"Where":[{"Condition":{"Comparison":{"ComparisonKind":2,"Left":{"Column":{"Expression":{"SourceRef":{"Source":"d"}},"Property":"Date"}},"Right":{"Literal":{"Value":"datetime'2020-04-01T00:00:00'"}}}}},{"Condition":{"In":{"Expressions":[{"Column":{"Expression":{"SourceRef":{"Source":"t"}},"Property":"County"}}],"Values":[[{"Literal":{"Value":"'Harris'"}}]]}}},{"Condition":{"Not":{"Expression":{"Comparison":{"ComparisonKind":0,"Left":{"Column":{"Expression":{"SourceRef":{"Source":"h"}},"Property":"Hospital Name"}},"Right":{"Literal":{"Value":"null"}}}}}}}]},"Binding":{"Primary":{"Groupings":[{"Projections":[0,1]}]},"DataReduction":{"DataVolume":2,"Primary":{"BinnedLineSample":{}}},"Version":1}}}]},"QueryId":"","ApplicationContext":{"DatasetId":"92bf5cbe-7a49-4548-a0b0-82e6a1d9ed1d","Sources":[{"ReportId":"db2a8e7a-2dc2-4ccd-8f8d-7aa98f5d424b"}]}}],"cancelQueries":[],"modelId":12328350    }

    payload = {
        "version": "1.0.0",
        "queries": [
            {
                "Query": {
                    "Commands": [
                        {
                            "SemanticQueryDataShapeCommand": {
                                "Query": {
                                    "Version": 2,
                                    "From": [
                                        {
                                            "Name": "h",
                                            "Entity": "Hospital_Info",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "d",
                                            "Entity": "Date",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "s1",
                                            "Entity": "SETRAC Measures",
                                            "Type": 0
                                        },
                                        {
                                            "Name": "t",
                                            "Entity": "TSA_County",
                                            "Type": 0
                                        }
                                    ],
                                    "Select": [
                                        {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {
                                                        "Source": "d"
                                                    }
                                                },
                                                "Property": "Date"
                                            },
                                            "Name": "Date.Date"
                                        },
                                        {
                                            "Measure": {
                                                "Expression": {
                                                    "SourceRef": {
                                                        "Source": "s1"
                                                    }
                                                },
                                                "Property": "Patients in General Beds (Suspected + Confirmed)"
                                            },
                                            "Name": "SurvData.Patients in General Beds (Suspected + Confirmed)"
                                        }
                                    ],
                                    "Where": [
                                        {
                                            "Condition": {
                                                "Comparison": {
                                                    "ComparisonKind": 2,
                                                    "Left": {
                                                        "Column": {
                                                            "Expression": {
                                                                "SourceRef": {
                                                                    "Source": "d"
                                                                }
                                                            },
                                                            "Property": "Date"
                                                        }
                                                    },
                                                    "Right": {
                                                        "Literal": {
                                                            "Value": "datetime'2020-04-01T00:00:00'"
                                                        }
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "In": {
                                                    "Expressions": [
                                                        {
                                                            "Column": {
                                                                "Expression": {
                                                                    "SourceRef": {
                                                                        "Source": "t"
                                                                    }
                                                                },
                                                                "Property": "County"
                                                            }
                                                        }
                                                    ],
                                                    "Values": [
                                                        [
                                                            {
                                                                "Literal": {
                                                                    "Value": f"'{county}'"
                                                                }
                                                            }
                                                        ]
                                                    ]
                                                }
                                            }
                                        },
                                        {
                                            "Condition": {
                                                "Not": {
                                                    "Expression": {
                                                        "Comparison": {
                                                            "ComparisonKind": 0,
                                                            "Left": {
                                                                "Column": {
                                                                    "Expression": {
                                                                        "SourceRef": {
                                                                            "Source": "h"
                                                                        }
                                                                    },
                                                                    "Property": "Hospital Name"
                                                                }
                                                            },
                                                            "Right": {
                                                                "Literal": {
                                                                    "Value": "null"
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                },
                                "Binding": {
                                    "Primary": {
                                        "Groupings": [
                                            {
                                                "Projections": [
                                                    0,
                                                    1,
                                                ]
                                            }
                                        ]
                                    },
                                    "DataReduction": {
                                        "DataVolume": 2,
                                        "Primary": {
                                            "BinnedLineSample": {}
                                        }
                                    },
                                    "Version": 1
                                }
                            }
                        }
                    ]
                },
                "QueryId": "",
                "ApplicationContext": {
                    "DatasetId": "d31709e8-3813-4fe6-9ed5-68720a203fa2",
                    "Sources": [
                        {
                            "ReportId": "7f7a5d35-838d-48ce-9db5-547dc585fdfd"
                        }
                    ]
                }
            }
        ],
        "cancelQueries": [],
        "modelId": 12388057
    }

    response = requests.post(query_url, json=payload, headers=headers).json()
    data = response['results'][0]['result']['data']['dsr']['DS'][0]['PH'][0]['DM0']
    df = parse_data(data, county)
    return df


icu_df = pd.DataFrame(columns=['Date', 'Level', 'values'])
gen_df = pd.DataFrame(columns=['Date', 'Level', 'values'])
counties = ['Angelina', 'Brazoria', 'Fort Bend', 'Harris', 'Galveston', 'Jefferson', 'Montgomery', 'Nacogdoches']

for county in counties:
    gen_df = gen_df.append(get_gen_data(county))
    icu_df = icu_df.append(get_icu_data(county))

# prepare merge
icu_df.columns = ['Date', 'Level', 'COVID_ICU']
gen_df.columns = ['Date', 'Level', 'COVID_General']

combined_df = pd.merge(icu_df, gen_df, on=['Date', 'Level'], how='outer')
date_max = combined_df['Date'].max()

# address instances where NA present in most recent date of df (excludes 5/22)
# done here instead of in parse_data to prevent creation of recent date when data isn't available
combined_df.fillna(method='ffill', inplace=True)

base_directory = 'C:/Users/jeffb/Desktop/Life/personal-projects/COVID/original-sources/historical/setrac/'
combined_df.to_csv(f'{base_directory}setrac_data_{date_max}.csv', index=False)
