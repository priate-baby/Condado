FROM python:3.11 as supervisor_api
COPY supervisor/api /app
WORKDIR /app
ENV PYTHONPATH=/app
RUN pip install -r requirements.txt
RUN curl -fsSL https://get.docker.com | sh

FROM node:20 as spa
COPY spa /app
WORKDIR /app
RUN npm install
RUN npm run build
