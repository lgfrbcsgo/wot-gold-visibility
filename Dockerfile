FROM heroku/heroku:16

RUN apt-get update
RUN apt-get install -y python3 python3-pip redis-server supervisor build-essential libmagick++-dev

WORKDIR /home

RUN wget https://www.imagemagick.org/download/releases/ImageMagick-6.9.10-5.tar.xz
RUN tar xvf ImageMagick-6.9.10-5.tar.xz
RUN cd ImageMagick-6.9.10-5 && ./configure && make && make install && ldconfig /usr/local/lib

WORKDIR /var/app

RUN pip3 install Flask==1.0.2
RUN pip3 install -U Flask-Cors==3.0.4
RUN pip3 install Wand==0.4.4
RUN pip3 install gunicorn
RUN pip3 install gunicorn[eventlet]
RUN pip3 install rq==0.10.0 redis==2.10.6
RUN pip3 install Flask-Dance==0.14.0
RUN pip3 install rq-dashboard==0.3.11

RUN sed -i -e 's/daemonize yes/daemonize no/g' /etc/redis/redis.conf

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV PORT 8080

COPY ./src /var/app
ADD supervisor.conf /etc/supervisor.conf

CMD supervisord -c /etc/supervisor.conf
