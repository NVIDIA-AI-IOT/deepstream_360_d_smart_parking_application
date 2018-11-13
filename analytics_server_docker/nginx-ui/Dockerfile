# build environment
FROM node:8 as ui-builder

LABEL stage=ui-builder

# Create app directory
WORKDIR /home/ui

COPY ui.zip .

RUN apt-get update && apt-get install unzip

RUN unzip ui.zip && rm ui.zip

RUN npm install

ARG REACT_APP_BACKEND_IP_ADDRESS

ARG REACT_APP_BACKEND_PORT

ARG REACT_APP_GOOGLE_MAP_API_KEY

ENV REACT_APP_BACKEND_IP_ADDRESS $REACT_APP_BACKEND_IP_ADDRESS

ENV REACT_APP_BACKEND_PORT $REACT_APP_BACKEND_PORT

ENV REACT_APP_GOOGLE_MAP_API_KEY $REACT_APP_GOOGLE_MAP_API_KEY

RUN npm run build

# production environment
FROM nginx

COPY --from=ui-builder /home/ui/build /usr/share/nginx/html

CMD ["nginx", "-g", "daemon off;"]