# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Mr-Snrub-Corp/snrub.api/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                         |    Stmts |     Miss |   Branch |   BrPart |     Cover |   Missing |
|--------------------------------------------- | -------: | -------: | -------: | -------: | --------: | --------: |
| app/\_\_init\_\_.py                          |        0 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/\_\_init\_\_.py              |        0 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/auth/\_\_init\_\_.py         |        0 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/auth/local.py                |       15 |        2 |        4 |        1 |     84.2% |    17, 34 |
| app/controllers/auth/password\_reset.py      |       56 |        3 |        8 |        0 |     95.3% |     89-91 |
| app/controllers/godmode.py                   |       44 |        1 |       12 |        1 |     96.4% |        44 |
| app/controllers/incident\_category.py        |       11 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/incident\_report.py          |       76 |        1 |       26 |        1 |     98.0% |       126 |
| app/controllers/incident\_report\_subject.py |       26 |        0 |        4 |        0 |    100.0% |           |
| app/controllers/incident\_type.py            |       20 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/telemetry.py                 |        7 |        0 |        0 |        0 |    100.0% |           |
| app/controllers/user.py                      |       71 |       12 |       20 |        8 |     78.0% |44, 50-51, 60, 65, 71-\>77, 74, 79-84, 106, 122 |
| app/core/\_\_init\_\_.py                     |        0 |        0 |        0 |        0 |    100.0% |           |
| app/core/config.py                           |       23 |        0 |        0 |        0 |    100.0% |           |
| app/db/crud\_base.py                         |      107 |        0 |       10 |        0 |    100.0% |           |
| app/db/database.py                           |        8 |        3 |        0 |        0 |     62.5% | 14, 19-20 |
| app/main.py                                  |       37 |        2 |        0 |        0 |     94.6% |    47, 66 |
| app/models/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100.0% |           |
| app/models/auth.py                           |       10 |        0 |        0 |        0 |    100.0% |           |
| app/models/godmode.py                        |       13 |        0 |        0 |        0 |    100.0% |           |
| app/models/incident\_category.py             |       12 |        0 |        0 |        0 |    100.0% |           |
| app/models/incident\_report.py               |       57 |        3 |        4 |        0 |     91.8% |     73-75 |
| app/models/incident\_report\_subject.py      |       17 |        0 |        0 |        0 |    100.0% |           |
| app/models/incident\_type.py                 |       35 |        1 |        4 |        1 |     94.9% |        50 |
| app/models/password\_reset.py                |       14 |        0 |        0 |        0 |    100.0% |           |
| app/models/user.py                           |       70 |        2 |       14 |        1 |     96.4% |  105, 120 |
| app/models/validators.py                     |        8 |        8 |        4 |        0 |      0.0% |      1-10 |
| app/routes/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100.0% |           |
| app/routes/admin.py                          |       11 |        5 |        0 |        0 |     54.5% |     12-16 |
| app/routes/auth/\_\_init\_\_.py              |        0 |        0 |        0 |        0 |    100.0% |           |
| app/routes/auth/google.py                    |       45 |        5 |        4 |        0 |     89.8% |25-26, 35-37 |
| app/routes/auth/local.py                     |       20 |        1 |        0 |        0 |     95.0% |        24 |
| app/routes/godmode.py                        |       14 |        0 |        0 |        0 |    100.0% |           |
| app/routes/incident\_category.py             |       13 |        0 |        0 |        0 |    100.0% |           |
| app/routes/incident\_report.py               |       25 |        0 |        0 |        0 |    100.0% |           |
| app/routes/incident\_report\_subject.py      |       18 |        0 |        0 |        0 |    100.0% |           |
| app/routes/incident\_type.py                 |       23 |        0 |        2 |        0 |    100.0% |           |
| app/routes/telemetry.py                      |       22 |       11 |        2 |        0 |     45.8% |     21-32 |
| app/routes/user.py                           |       39 |        3 |        6 |        2 |     88.9% |44, 94, 97 |
| app/security/\_\_init\_\_.py                 |        0 |        0 |        0 |        0 |    100.0% |           |
| app/security/auth\_bearer.py                 |       25 |        5 |        8 |        4 |     72.7% |19, 21, 24, 32-33, 34-\>37 |
| app/security/authorization.py                |       48 |       15 |       14 |        2 |     62.9% |32, 46, 75-90 |
| app/security/jwt.py                          |       16 |        1 |        0 |        0 |     93.8% |        12 |
| app/security/oauth\_client.py                |        5 |        0 |        0 |        0 |    100.0% |           |
| app/services/email.py                        |       13 |        0 |        0 |        0 |    100.0% |           |
| app/services/image\_processing.py            |       11 |        0 |        0 |        0 |    100.0% |           |
| app/services/telemetry.py                    |       42 |        1 |       12 |        1 |     96.3% |       199 |
| **TOTAL**                                    | **1127** |   **85** |  **158** |   **22** | **90.6%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/Mr-Snrub-Corp/snrub.api/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/Mr-Snrub-Corp/snrub.api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Mr-Snrub-Corp/snrub.api/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/Mr-Snrub-Corp/snrub.api/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FMr-Snrub-Corp%2Fsnrub.api%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/Mr-Snrub-Corp/snrub.api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.