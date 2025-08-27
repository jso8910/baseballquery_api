###########
# BUILDER #
###########

# pull official base image
FROM python:3.13-slim as builder

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

# lint
RUN pip install --upgrade pip
COPY . /usr/src/app/

# install python dependencies
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt


#########
# FINAL #
#########

# pull official base image
FROM python:3.13-slim

# create directory for the app user
RUN mkdir -p /home/app

# create the app user
RUN addgroup --system app && adduser --system --group app

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends netcat-traditional curl build-essential
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

# Install chadwick
WORKDIR $HOME
RUN curl -L https://github.com/chadwickbureau/chadwick/releases/download/v0.10.0/chadwick-0.10.0.tar.gz | tar xz
WORKDIR $HOME/chadwick-0.10.0
RUN ./configure
RUN make
RUN make install

WORKDIR $APP_HOME


# copy entrypoint.sh
COPY ./entrypoint.sh $APP_HOME
RUN chmod +x $APP_HOME/entrypoint.sh

# copy project
COPY . $APP_HOME

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# chown .baseballquery
RUN mkdir -p $HOME/.baseballquery
RUN chown -R app:app $HOME/.baseballquery
VOLUME $HOME/.baseballquery

# chown lmdb_db
RUN mkdir -p $HOME/lmdb_db
RUN chown -R app:app $HOME/lmdb_db
VOLUME $HOME/lmdb_db

# chown db.sqlite3
RUN touch $APP_HOME/db.sqlite3
RUN chown app:app $APP_HOME/db.sqlite3
VOLUME $APP_HOME/db.sqlite3

# change to the app user
USER app

# ENTRYPOINT ["$APP_HOME/entrypoint.sh"]