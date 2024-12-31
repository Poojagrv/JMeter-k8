# Base image
FROM openjdk:11-jre-slim
# Environment variables
ENV JMETER_VERSION=5.5
ENV JMETER_HOME /opt/apache-jmeter-${JMETER_VERSION}
ENV PATH $JMETER_HOME/bin:$PATH
# Install JMeter
RUN apt-get update && \
   apt-get install -y wget unzip git && \
   wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz && \
   tar -xzf apache-jmeter-${JMETER_VERSION}.tgz -C /opt && \
   rm apache-jmeter-${JMETER_VERSION}.tgz
# Copy ulp-observability-plugin.jar from local machine to Docker image
#COPY ulp-observability-listener-1.0.4.jar $JMETER_HOME/lib/ext/
COPY lib $JMETER_HOME/lib

RUN ls -l $JMETER_HOME/lib/ext

# Copy the API server code
COPY api /api
# Copy the user properties file
COPY user.properties $JMETER_HOME/bin/
# Install dependencies for API server
RUN apt-get install -y python3 python3-pip
RUN pip3 install flask psutil kubernetes
# Set the working directory
WORKDIR /api
# Create a directory for Git clones
RUN mkdir -p /app/git_clones
RUN mkdir -p /app/logs
# Expose the ports for the API
EXPOSE 5000
# Start JMeter and API server
CMD ["sh", "-c", "jmeter-server & python3 api_server.py"]