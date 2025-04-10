#!/bin/bash

# RDS connection details
DB_HOST="imagedatabase.cnwyqwsus01i.us-east-1.rds.amazonaws.com"           # Replace with your RDS endpoint
DB_USER="admin"           # Your RDS admin username
DB_PASSWORD="assignment-password"       # Your RDS password
SQL_COMMANDS=$(cat <<EOF
/*
  Database Creation Script for the Image Captioning App
*/

DROP DATABASE IF EXISTS imagedatabase;
CREATE DATABASE imagedatabase;
USE imagedatabase;

/* Create captions table to store image captions */
CREATE TABLE captions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_key VARCHAR(255) NOT NULL,
    caption TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF
)

# Execute SQL commands
echo "Creating database and table..."
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "$SQL_COMMANDS"

# Check if the previous command was successful
if [ $? -eq 0 ]; then
    echo "Database and table created successfully!"
else
    echo "Error: Failed to create database and table. Please check the connection details and try again."
    exit 1
fi
