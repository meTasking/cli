# pull official base image
FROM docker.io/library/python:3.12.4

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV TZ=Europe/Prague
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HOST "0.0.0.0"
ENV PORT 80
ENV PUBLIC_URL "http://localhost:80"
ENV TITLE ""
ENV METASKING_SERVER "http://localhost:8000"

# set command to run when container starts
ENTRYPOINT ["python", "serve.py", "$HOST", "$PORT", "$PUBLIC_URL", "$TITLE"]

# install python dependencies
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# add app
COPY . .
