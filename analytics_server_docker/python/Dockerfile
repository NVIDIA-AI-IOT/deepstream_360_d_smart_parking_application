FROM python:3.6

WORKDIR /home/python-tracker-module

COPY tracker.zip .

RUN apt-get update && apt-get install unzip

ENV PYTHONPATH /home/python-tracker-module/code

RUN unzip tracker.zip && rm tracker.zip

RUN pip install -r requirements.txt

CMD ["python", "usecasecode/360d/stream_track.py","--sconfig=/home/python-tracker-module/config/config_360d_stream.json","--config=/home/python-tracker-module/config/config_360d.json"]