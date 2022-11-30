# Data Engineering Take Home: ETL off a SQS Queue #

This application reads the messages from an AWS SQS Queue running via localstack within a Docker container, stores them in a Pandas DataFrame, masks the ip and device_id fields of each message, and writes the DataFrame to a Postgres database running within another Docker container.

## How do I run the application?

The setup for this application is identical to that of the initial exercise, restated here:

1. Fork this repository to a personal Github, GitLab, Bitbucket, etc... account.
2. You will need the following installed on your local machine
    * make
        * Ubuntu -- `apt-get -y install make`
        * Windows -- `choco install make`
        * Mac -- `brew install make`
    * python3 -- [python install guide](https://www.python.org/downloads/)
    * pip3 -- `python -m ensurepip --upgrade` or run `make pip-install` in the project root
    * awslocal -- `pip install awscli-local`  or run `make pip install` in the project root
    * docker -- [docker install guide](https://docs.docker.com/get-docker/)
    * docker-compose -- [docker-compose install guide]()
3. Run `make start` to execute the docker-compose file in the the project (see scripts/ and data/ directories to see what's going on, if you're curious)
    * An AWS SQS Queue is created
    * A script is run to write 100 JSON records to the queue
    * A Postgres database will be stood up
    * A user_logins table will be created in the public schema

After the setup is complete, simply run the following command in the project root:

```
python3 main.py
```

This will run the application, read and delete the messages from the SQS Queue, and write the data (including masked fields) to the Postgres database.

### *Notes on updates made to setup files* ###

A few modifications were made to the setup files included in the exercise:
1. The requirements.txt file has been updated to reflect the required environment configuration for this project, so no packages will need to be manually installed.
2. The Makefile has also been updated, with `*program name* not found` as the first argument to the `ifeq` conditionals to ensure it runs properly.
3. The type for the `app_version` column within the CREATE command of `create_table.sql` has been changed from `integer` to `varchar(32)`, which reflects the actual values of the `app_version` field within the SQS messages.

## Thought process ##

While planning my approach for completing this exercise, I broke it down into 8 individual tasks.

1. Connect to the SQS Queue in the localstack Docker container.
2. Read each message in the queue, extracting the body and timestamp into a DataFrame using pandas. Delete each message from the queue after handling.
3. Check the DataFrame for rows with matching `ip` values, recording the indices.
4. Iterate through the rows in the DataFrame, masking each unique `ip` and checking each `ip` with a duplicated value against a dictionary of masked duplicated `ip`s. Add `masked_ip`s to a list.
    * The dictionary has the format `{ip: masked_ip}`
    * If the `ip` matches one already in the dictionary, use the corresponding mask.
    * If the `ip` does not match one in the dictionary, generate a new `masked_ip`, add to the dictionary, and add to the list.
5. Iterate through the rows in the DataFrame, masking each unique `device_id` and checking each `device_id` with a duplicated value against a dictionary of masked duplicated `device_id`s. Add `masked_device_id`s to a list.
    * The dictionary has the format `{device_id: masked_device_id}`
    * If the `device_id` matches one already in the dictionary, use the corresponding mask.
    * If the `device_id` does not match one in the dictionary, generate a new `masked_device_id`, add to the dictionary, and add to the list.
6. Create a new DataFrame with columns `'user_id', 'device_type', 'masked_ip', 'masked_device_id', 'locale', 'app_version', 'create_date'`
    * `masked_ip` and `masked_device_id` are drawn from their corresponding lists, while `create_date` comes from the `timestamp`.
7. Connect to the Postgres database.
8. Write the final DataFrame to the `user-logins` table in the database.

### *Reading from the Queue* ###

To read the messages from the queue, I used a while loop to read each message via the `receive_message()` function as long as `receive_messages()` yielded a dictionary with a `'Messages'` key. If so, it calls the `handle_message()` function defined earlier to extract the body of the message (using `json.loads`) and the timestamp (by accessing `resp['ResponseMetadata']['HTTPHeaders']['date']`). As a JSON object, the body is already a dict object. The timestamp must be placed in a dict object with the key `create_date`, corresponding with the column in `user-logins`. After each message is read and handled, it is deleted using the `delete_message()` function.

### *Data Structures* ###

I chose to use pandas DataFrames to work with the data because, honestly, it's the option I understand the best. Being able to generate a visual representation of the data before writing it to the Postgres database was helpful for recognizing errors and issues, and it's simple to convert JSON objects into DataFrames.

Along the same lines, I stored the masked `device_id`s and `ip`s in lists because they are easily added to DataFrames as columns.

### *Masking Data* ###

In order to mask the ip addresses, I used the `fake.ipv4()` function from the faker library to generate a random ip address. To mask the device ids, I used `random.randint()` from the random library concatenated together with hyphens to generate random device ids.

In order to ensure values in the `device_id` or `ip` columns that were duplicated in another message matched even after masking, I first created a list of indices in the DataFrame which contained values duplicated elsewhere. When those indices are reached while iterating through the rows, the value from the relevant column is compared against a dictionary containing values and their masks (format: `{value: masked_value}`). If the value is found in the keys of the dict, the corresponding masked_value is appended to the list. If not, a new masked_value is generated, added with its value to the dict, and appended to the list.

### *Postgres* ###

I connected to the Postgres database using the `create_engine()` function in the sqlalchemy library. Again, I did this because of its compatibility with pandas -- the `pandas.to_sql()` function only works using sqlalchemy or sqlite to connect. Once the final DataFrame was constructed, I wrote it to the `user-logins` table in the Postgres database using the `pandas.to_sql()` function.

## Next Steps ##

The two obvious next steps would be adding functions to mask the other columns and working to increase the efficiency of the application overall. While pandas DataFrames are a great way to visualize data, iterating through the rows is not a particularly efficient or fast process. It works for 100 rows, but it wouldn't scale to, say, reading 1,000 messages from the queue.

A more involved next step might be finding a way to not only read messages from the queue, but also to mask columns that are already included in the table. Sqlalchemy doesn't have an easy way to do this, but it might be possible to use the `psycopg2` library's cursor object do read, modify, and replace data already written to the table.


### Original ReadMe text ###
=====

# Fetch Rewards #
## Data Engineering Take Home: ETL off a SQS Qeueue ##

You may use any programming language to complete this exercise. We strongly encourage you to write a README to explain how to run your application and summarize your thought process.

## What do I need to do?
This challenge will focus on your ability to write a small application that can read from an AWS SQS Qeueue, transform that data, then write to a Postgres database. This project includes steps for using docker to run all the components locally, **you do not need an AWS account to do this take home.**

Your objective is to read JSON data containing user login behavior from an AWS SQS Queue that is made available via [localstack](https://github.com/localstack/localstack). Fetch wants to hide personal identifiable information (PII). The fields `device_id` and `ip` should be masked, but in a way where it is easy for data analysts to identify duplicate values in those fields.

Once you have flattened the JSON data object and masked those two fields, write each record to a Postgres database that is made available via [Postgres's docker image](https://hub.docker.com/_/postgres). Note the target table's DDL is:

```sql
-- Creation of user_logins table

CREATE TABLE IF NOT EXISTS user_logins(
    user_id             varchar(128),
    device_type         varchar(32),
    masked_ip           varchar(256),
    masked_device_id    varchar(256),
    locale              varchar(32),
    app_version         integer,
    create_date         date
);
```

You will have to make a number of decisions as you develop this solution:

*    How will you read messages from the queue?
*    What type of data structures should be used?
*    How will you mask the PII data so that duplicate values can be identified?
*    What will be your strategy for connecting and writing to Postgres?
*    Where and how will your application run?

**The recommended time to spend on this take home is 2-3 hours.** Make use of code stubs, doc strings, and a next steps section in your README to elaborate on ways that you would continue fleshing out this project if you had the time. For this assignment an ounce of communication and organization is worth a pound of execution.

## Project Setup
1. Fork this repository to a personal Github, GitLab, Bitbucket, etc... account. We will not accept PRs to this project.
2. You will need the following installed on your local machine
    * make
        * Ubuntu -- `apt-get -y install make`
        * Windows -- `choco install make`
        * Mac -- `brew install make`
    * python3 -- [python install guide](https://www.python.org/downloads/)
    * pip3 -- `python -m ensurepip --upgrade` or run `make pip-install` in the project root
    * awslocal -- `pip install awscli-local`  or run `make pip install` in the project root
    * docker -- [docker install guide](https://docs.docker.com/get-docker/)
    * docker-compose -- [docker-compose install guide]()
3. Run `make start` to execute the docker-compose file in the the project (see scripts/ and data/ directories to see what's going on, if you're curious)
    * An AWS SQS Queue is created
    * A script is run to write 100 JSON records to the queue
    * A Postgres database will be stood up
    * A user_logins table will be created in the public schema
4. Test local access
    * Read a message from the queue using awslocal, `awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/login-queue`
    * Connect to the Postgres database, verify the table is created
    * username = `postgres`
    * database = `postgres`
    * password = `postgres`

```bash
# password: postgres

psql -d postgres -U postgres  -p 5432 -h localhost -W
Password: 

postgres=# select * from user_logins;
 user_id | device_type | hashed_ip | hashed_device_id | locale | app_version | create_date 
---------+-------------+-----------+------------------+--------+-------------+-------------
(0 rows)
```
5. Run `make stop` to terminate the docker containers and optionally run `make clean` to clean up docker resources.

## All done, now what?
Upload your codebase to a public Git repo (GitHub, Bitbucket, etc.) and email us the link.  Please double-check this is publicly accessible.

Please assume the evaluator does not have prior experience executing programs in your chosen language and needs documentation understand how to run your code
