# Required Diagrams

## Figure 6.2: ER Diagram

```mermaid
erDiagram
    USERS {
        int user_id PK
        varchar email
        varchar password
        varchar role
        int reference_id
    }

    STUDENT {
        int student_id PK
        varchar name
        varchar course
        varchar reg_no
        int semester
        tinyint is_active
    }

    TEACHER {
        int teacher_id PK
        varchar name
        varchar email
    }

    SUBJECT {
        int subject_id PK
        varchar subject_name
        int semester
        varchar course
    }

    TEACHER_SUBJECT {
        int id PK
        int teacher_id FK
        int subject_id FK
    }

    ATTENDANCE {
        int attendance_id PK
        int student_id FK
        int subject_id FK
        int teacher_id FK
        date attendance_date
        time attendance_time
        varchar status
    }

    TEACHER ||--o{ TEACHER_SUBJECT : teaches
    SUBJECT ||--o{ TEACHER_SUBJECT : assigned
    STUDENT ||--o{ ATTENDANCE : has
    TEACHER ||--o{ ATTENDANCE : marks
    SUBJECT ||--o{ ATTENDANCE : contains
    USERS }o--|| TEACHER : login_for
    USERS }o--|| STUDENT : login_for
```

## Figure 6.3.1: Login Module DFD

```mermaid
flowchart TD
    A[User] --> B[Enter Email and Password]
    B --> C[Login Form]
    C --> D[Flask Login Controller]
    D --> E[(Users Table)]
    E --> F{Credentials Valid?}
    F -- Yes --> G[Create Session]
    G --> H[Redirect to Dashboard]
    F -- No --> I[Display Invalid Login Message]
    I --> C
```

## Figure 6.3.2: Face Capture Module DFD

```mermaid
flowchart TD
    A[Teacher] --> B[Open Add Student Page]
    B --> C[Enter Student Details]
    C --> D[Save Student Details]
    D --> E[(Student Table)]
    D --> F[Create Student Dataset Folder]
    F --> G[Start Camera]
    G --> H[Capture 50 Face Images]
    H --> I[Upload Images]
    I --> J[Store Images in Dataset Folder]
    J --> K[Registration Completed]
```

## Figure 6.3.3: Recognition Module DFD

```mermaid
flowchart TD
    A[Teacher] --> B[Select Subject]
    B --> C[Start Camera]
    C --> D[Capture Live Face Image]
    D --> E[Extract Face Features]
    E --> F[Load Trained SVM Model]
    F --> G[Predict Student ID]
    G --> H{Confidence >= Threshold?}
    H -- Yes --> I[Fetch Student Name]
    I --> J[(Student Table)]
    H -- No --> K[Show Not Recognized Message]
```

## Figure 6.3.4: Attendance Module DFD

```mermaid
flowchart TD
    A[Recognized Student ID] --> B[Selected Subject ID]
    B --> C[Check Teacher Authorization]
    C --> D{Authorized?}
    D -- No --> E[Show Not Authorized Message]
    D -- Yes --> F[Check Existing Attendance]
    F --> G{Already Marked Today?}
    G -- Yes --> H[Show Already Marked Message]
    G -- No --> I[Insert Attendance Record]
    I --> J[(Attendance Table)]
    J --> K[Show Attendance Marked Message]
```

## Figure 6.4: Use Case Diagram

```plantuml
@startuml
left to right direction

actor Teacher
actor Student
actor Admin

rectangle "Digital Facial Recognition Attendance System" {
    usecase "Login" as UC1
    usecase "Signup / Create User Account" as UC2
    usecase "View Dashboard" as UC3
    usecase "Add Student Details" as UC4
    usecase "Capture Student Face Images" as UC5
    usecase "Train Face Recognition Model" as UC6
    usecase "Select Subject" as UC7
    usecase "Mark Attendance" as UC8
    usecase "Recognize Face" as UC9
    usecase "Check Teacher Subject Authorization" as UC10
    usecase "Prevent Duplicate Attendance" as UC11
    usecase "View Attendance Records" as UC12
    usecase "Download Attendance CSV" as UC13
    usecase "Delete Student" as UC14
    usecase "Logout" as UC15
}

Teacher --> UC1
Teacher --> UC3
Teacher --> UC4
Teacher --> UC5
Teacher --> UC6
Teacher --> UC7
Teacher --> UC8
Teacher --> UC12
Teacher --> UC13
Teacher --> UC14
Teacher --> UC15

Student --> UC1
Student --> UC3
Student --> UC12
Student --> UC15

Admin --> UC2
Admin --> UC1
Admin --> UC12
Admin --> UC13
Admin --> UC15

UC4 ..> UC5 : <<include>>
UC8 ..> UC7 : <<include>>
UC8 ..> UC9 : <<include>>
UC8 ..> UC10 : <<include>>
UC8 ..> UC11 : <<include>>
UC13 ..> UC12 : <<extend>>

@enduml
```

## Figure 7.1: Authentication Module Diagram

```mermaid
flowchart TD
    A[Start] --> B[Open Login or Signup Page]
    B --> C{New User?}
    C -- Yes --> D[Enter Signup Details]
    D --> E[Store User Account]
    E --> F[(Users Table)]
    F --> G[Redirect to Login]
    C -- No --> H[Enter Login Credentials]
    H --> I[Validate Credentials]
    I --> J{Valid User?}
    J -- Yes --> K[Create User Session]
    K --> L[Open Dashboard]
    J -- No --> M[Show Error Message]
    M --> H
```

## Figure 7.2: Student Registration Module Diagram

```mermaid
flowchart TD
    A[Teacher Dashboard] --> B[Add Student]
    B --> C[Enter Name, Reg No, Course, Semester]
    C --> D{Details Valid?}
    D -- No --> E[Show Validation Error]
    D -- Yes --> F[Insert Student Record]
    F --> G[(Student Table)]
    F --> H[Generate Student ID]
    H --> I[Create Dataset Folder]
    I --> J[Enable Face Capture]
```

## Figure 7.3: Face Capture Module Diagram

```mermaid
flowchart TD
    A[Start Capture] --> B[Request Camera Permission]
    B --> C{Permission Granted?}
    C -- No --> D[Show Camera Error]
    C -- Yes --> E[Open Webcam Stream]
    E --> F[Capture Image Frame]
    F --> G[Convert Frame to JPEG]
    G --> H[Add Image to Upload List]
    H --> I{50 Images Captured?}
    I -- No --> F
    I -- Yes --> J[Upload Images to Server]
    J --> K[Save Images in Student Folder]
    K --> L[Capture Completed]
```

## Figure 7.4: Model Training Module Diagram

```mermaid
flowchart TD
    A[Click Train Model] --> B[Read Dataset Folders]
    B --> C[Load Student Images]
    C --> D[Convert Images to Grayscale]
    D --> E[Resize Images to 64 x 64]
    E --> F[Flatten Image Features]
    F --> G[Normalize Features using StandardScaler]
    G --> H[Train SVM Classifier]
    H --> I[Save Model and Scaler]
    I --> J[model.pkl Created]
    J --> K[Training Completed]
```

## Figure 7.5: Face Recognition Module Diagram

```mermaid
flowchart TD
    A[Live Camera Frame] --> B[Receive Image in Backend]
    B --> C[Decode Image]
    C --> D[Convert to Grayscale]
    D --> E[Resize to 64 x 64]
    E --> F[Flatten Feature Vector]
    F --> G[Apply Saved Scaler]
    G --> H[Predict using SVM Model]
    H --> I{Confidence Sufficient?}
    I -- Yes --> J[Return Student ID and Name]
    I -- No --> K[Return Low Confidence Response]
```

## Figure 7.6: Attendance Management Module Diagram

```mermaid
flowchart TD
    A[Recognized Student] --> B[Get Current Date and Time]
    B --> C[Check Subject Selection]
    C --> D[Check Teacher Subject Mapping]
    D --> E{Valid Mapping?}
    E -- No --> F[Reject Attendance]
    E -- Yes --> G[Check Duplicate Attendance]
    G --> H{Record Exists?}
    H -- Yes --> I[Return Already Marked]
    H -- No --> J[Save Attendance as Present]
    J --> K[(Attendance Table)]
    K --> L[Update Attendance Records]
```

## Figure 7.7: Report Generation Module Diagram

```mermaid
flowchart TD
    A[Teacher or Admin] --> B[Open Attendance Records Page]
    B --> C[Fetch Attendance Records]
    C --> D[(Attendance Table)]
    D --> E[Join Student, Subject and Teacher Data]
    E --> F[Display Records in Table]
    F --> G{Download Required?}
    G -- No --> H[View Records on Screen]
    G -- Yes --> I[Generate CSV File]
    I --> J[Download attendance.csv]
```
