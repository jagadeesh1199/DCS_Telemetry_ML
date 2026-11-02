import sys
print(sys.executable)
# Must show: ...envs\pyspark_env\python.exe

import os
# Java is conda-installed so JAVA_HOME is set automatically — test without manual override
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("Test").getOrCreate()
print(spark.version)  # Should print 3.5.1