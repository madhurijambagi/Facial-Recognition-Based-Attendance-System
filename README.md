# \# 🎓 Digital Facial Recognition Attendance System

# 

# A \*\*Flask-based Facial Attendance System\*\* that uses \*\*Machine Learning (SVM)\*\* and \*\*Computer Vision (OpenCV)\*\* to automatically detect and mark student attendance in real-time.

# 

# \---

# 

# \## 🚀 Project Overview

# 

# This system captures student faces using a webcam, trains a machine learning model, and recognizes students to mark attendance automatically in a \*\*MySQL database\*\*.

# 

# It replaces manual attendance with a \*\*fast, accurate, and secure system\*\*.

# 

# \---

# 

# \## 🧠 Core Technologies Used

# 

# \* \*\*Python (Flask)\*\* – Backend

# \* \*\*OpenCV\*\* – Image processing

# \* \*\*Scikit-learn (SVM)\*\* – Face classification

# \* \*\*StandardScaler\*\* – Feature normalization

# \* \*\*MySQL\*\* – Database

# \* \*\*HTML, CSS, JavaScript\*\* – Frontend

# 

# \---

# 

# \## ⚙️ How the System Works

# 

# \### 1. Add Student

# 

# \* Enter student details

# \* Capture \*\*50 images using webcam\*\*

# \* Images stored in dataset folder

# 

# 👉 Implemented in:

# `add\_student.html` + camera logic

# 

# 

# \---

# 

# \### 2. Train Model

# 

# \* Images converted to grayscale

# \* Resized to \*\*64×64\*\*

# \* Flattened into vectors

# \* Scaled using StandardScaler

# \* Trained using \*\*SVM classifier\*\*

# 

# 👉 Training logic:

# 

# 

# \---

# 

# \### 3. Face Recognition

# 

# \* Webcam captures live frame

# \* Extracts face embedding

# \* Model predicts student ID

# \* Confidence score generated

# 

# 👉 Recognition logic:

# 

# 

# \---

# 

# \### 4. Mark Attendance

# 

# \* Recognized student → marked \*\*Present\*\*

# \* Stored with:

# 

# &#x20; \* Date

# &#x20; \* Time

# &#x20; \* Subject

# &#x20; \* Teacher

# 

# 👉 Frontend logic:

# 

# 

# \---

# 

# \## 🗄️ Database Design (MySQL)

# 

# Database: `facial\_attendance\_mini\_project`

# 

# \### Tables:

# 

# \### 👨‍🎓 student

# 

# \* student\_id (PK)

# \* name

# \* reg\_no

# \* course

# \* semester

# \* face\_encoding

# 

# \---

# 

# \### 📘 subject

# 

# \* subject\_id (PK)

# \* subject\_name

# \* semester

# \* course

# 

# \---

# 

# \### 👩‍🏫 teacher

# 

# \* teacher\_id (PK)

# \* name

# \* email

# 

# \---

# 

# \### 🔗 teacher\_subject

# 

# \* teacher\_id

# \* subject\_id

# \* class\_id

# 

# \---

# 

# \### 📊 attendance

# 

# \* attendance\_id (PK)

# \* student\_id (FK)

# \* subject\_id (FK)

# \* teacher\_id (FK)

# \* attendance\_date

# \* attendance\_time

# \* status (Present/Absent)

# 

# \---

# 

# \### 🔐 users (Login System)

# 

# \* email

# \* password

# \* role (teacher/admin/student)

# \* reference\_id

# 

# \---

# 

# \## 🔐 Authentication System

# 

# \* Login \& Signup system implemented

# \* Role-based access:

# 

# &#x20; \* Teacher

# &#x20; \* Student

# &#x20; \* Admin

# 

# 👉 Files:

# 

# \* Login page: 

# \* Signup page: 

# 

# \---

# 

# \## 📊 Dashboard Features

# 

# \* Attendance statistics (chart)

# \* Recent attendance records

# \* Model training progress

# \* Subject-wise filtering

# 

# 👉 Dashboard logic:

# 

# 

# \---

# 

# \## 📷 Key Features

# 

# ✅ Real-time face recognition

# ✅ Automatic attendance marking

# ✅ Role-based login system

# ✅ Model training with progress tracking

# ✅ MySQL database integration

# ✅ Clean UI dashboard

# ✅ CSV export support

# 

# \---

# 

# \## 📂 Project Structure

# 

# ```

# project/

# │

# ├── app.py

# ├── model.py

# ├── model.pkl

# ├── dataset/

# │   ├── 48/

# │   ├── 49/

# │   ├── 54/

# │   └── ...

# │

# ├── templates/

# │   ├── index.html

# │   ├── login.html

# │   ├── signup.html

# │   ├── add\_student.html

# │   ├── mark\_attendance.html

# │   └── attendance\_record.html

# │

# ├── static/

# │   ├── css/

# │   ├── js/

# │   └── images/

# │

# └── train\_status.json

# ```

# 

# \---

# 

# \## ▶️ How to Run

# 

# \### 1. Install dependencies

# 

# ```bash

# pip install flask opencv-python numpy scikit-learn mysql-connector-python

# ```

# 

# \---

# 

# \### 2. Setup MySQL

# 

# Create database:

# 

# ```sql

# CREATE DATABASE facial\_attendance\_mini\_project;

# ```

# 

# Import tables manually or using script.

# 

# \---

# 

# \### 3. Run application

# 

# ```bash

# python app.py

# ```

# 

# Open:

# 

# ```

# http://127.0.0.1:5000

# ```

# 

# \---

# 

# \## 📈 Sample Output

# 

# \* Students recognized with \*\*80–95% accuracy\*\*

# \* Attendance stored with timestamp

# \* Real-time dashboard updates

# 

# \---

# 

# \## ⚠️ Limitations

# 

# \* Requires good lighting

# \* Accuracy depends on dataset quality

# \* No deep learning (uses basic ML - SVM)

# 

# \---

# 

# \## 🔮 Future Improvements

# 

# \* CNN / Deep Learning model

# \* Face detection using Haarcascade / MTCNN

# \* Mobile app integration

# \* Multi-camera support

# \* Cloud deployment

# 

# \---

# 

# \## 👩‍💻 Author

# 

# Madhuri

# MCA Student | Computer Science Enthusiast

# 

# \---

# 

# \## ⭐ Final Note

# 

# This project demonstrates:

# 

# \* Machine Learning (SVM)

# \* Computer Vision

# \* Full-stack development

# \* Database design

# 

# Perfect for \*\*college projects, internships, and placements\*\* 🚀



