FROM node:8

# Create app directory
WORKDIR /home/node

COPY apis.zip .

RUN apt-get update && apt-get install unzip

RUN unzip apis.zip && rm apis.zip

RUN npm install
