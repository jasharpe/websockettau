FROM python:2

RUN pip install tornado backports.ssl_match_hostname sqlalchemy pymysql

ADD *.py /websockettau/
ADD templates/* /websockettau/templates/
ADD static/* /websockettau/static/
ADD localhost.* /websockettau/
ADD chained.pem /websockettau/
ADD domain.key /websockettau/

WORKDIR /websockettau/
ENTRYPOINT [ "python", "./tau.py", "--debug", "--port=8000", "--ssl_port=8001" ]
