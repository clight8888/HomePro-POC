# HomePro Mobile App Development Specification

## 📱 Overview
This document provides a comprehensive specification for developing iOS and Android mobile applications that match the functionality of the HomePro web platform. HomePro is a home improvement project management platform that connects homeowners with contractors through an intelligent bidding system.

---

## 🎯 Core Features Summary

### **Primary User Types**
1. **Homeowners** - Submit projects, review bids, manage contractors
2. **Contractors** - Browse projects, submit bids, communicate with homeowners
3. **Admins** - Platform management and moderation
4. **Guests** - Limited project submission without registration

### **Key Functionality**
- AI-powered project submission (audio/text/video)
- Real-time bidding system
- Messaging and notifications
- Project management workflow
- User authentication and profiles
- Admin dashboard and analytics

---

## 🏗️ Technical Architecture

### **Backend API Endpoints**
The mobile app will communicate with the existing Flask backend via REST API calls:

**Base URL:** `https://your-domain.com` or `http://your-ec2-ip:8000`

### **Authentication System**
- Session-based authentication with Flask-Login
- Role-based access control (homeowner/contractor/admin)
- Guest user support with session management

---

## 📋 Detailed Feature Specifications

## 1. Authentication & User Management

### 1.1 Login Screen (`/login`)
**API Endpoint:** `POST /login`

**UI Components:**
- Email input field (validation: email format)
- Password input field (secure text entry)
- "Remember Me" checkbox
- Login button
- "Forgot Password" link
- "Register" navigation link
- Guest access option

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "userpassword"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "homeowner",
    "is_admin": false
  },
  "redirect": "/dashboard"
}
```

### 1.2 Registration Screen (`/register`)
**API Endpoint:** `POST /register`

**UI Components:**
- First Name input
- Last Name input
- Email input (with validation)
- Password input (with strength indicator)
- Confirm Password input
- Role selection (Homeowner/Contractor radio buttons)
- Terms & Conditions checkbox
- Register button
- "Already have account?" login link

**Additional Fields for Contractors:**
- Company name (optional)
- Location
- Specialties (multi-select: Plumbing, Electrical, Kitchen, Bathroom, etc.)
- Business information (text area)

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "password": "securepassword",
  "role": "homeowner",
  "location": "New York, NY",
  "company": "ABC Contracting",
  "specialties": ["plumbing", "electrical"],
  "business_info": "Licensed contractor with 10 years experience"
}
```

### 1.3 Guest Registration (`/guest_register`)
**API Endpoint:** `POST /guest_register`

**UI Components:**
- Name input
- Email input
- Phone input (optional)
- Project submission form (simplified)
- "Register Later" option

---

## 2. Dashboard Screens

### 2.1 Homeowner Dashboard (`/dashboard`)
**API Endpoint:** `GET /dashboard`

**UI Components:**
- Welcome header with user name
- Quick stats cards:
  - Active Projects count
  - Total Bids Received count
  - Completed Projects count
- "Submit New Project" prominent button
- Recent Projects list (with status indicators)
- Recent Bids section
- Quick actions menu

**Project Status Indicators:**
- 🟢 Active (accepting bids)
- 🔵 In Progress (contractor assigned)
- ✅ Completed
- ⭕ Closed

### 2.2 Contractor Dashboard (`/dashboard`)
**API Endpoint:** `GET /dashboard`

**UI Components:**
- Welcome header with contractor name
- Quick stats cards:
  - Available Projects count
  - Active Bids count
  - Won Projects count
  - Success Rate percentage
- "Browse Projects" prominent button
- Available Projects list (filterable)
- My Bids section with status
- Messages/Notifications indicator

**Project Filters:**
- Project Type (dropdown)
- Budget Range (slider)
- Location (search/dropdown)
- Timeline (dropdown)

---

## 3. Project Management

### 3.1 Submit Project Screen (`/submit_project`)
**API Endpoints:** 
- `GET /submit_project` (form)
- `POST /submit_project` (submission)
- `POST /process_audio` (audio processing)
- `POST /process_audio_transcript` (transcript processing)

**UI Components:**

**Method Selection:**
- Audio Recording button (with waveform visualization)
- Text Input option
- File Upload option (audio/video)

**Audio Recording Interface:**
- Record button (red when recording)
- Stop button
- Play/Pause controls
- Waveform visualization
- Recording timer
- Re-record option

**Project Details Form:**
- Title input (auto-populated from AI)
- Description text area (auto-populated from AI)
- Project Type dropdown (auto-selected from AI)
- Location input (with GPS option)
- Budget range slider (min/max)
- Timeline dropdown
- Additional notes text area

**AI Processing Flow:**
1. Upload/record audio → `POST /process_audio`
2. Show processing status → `GET /processing_status/<process_id>`
3. Review AI-generated details → `GET /review_project`
4. Confirm and post → `POST /confirm_project`

**Request Body (Audio):**
```json
{
  "audio_file": "base64_encoded_audio_data",
  "file_type": "audio/mp3"
}
```

**AI Processing Response:**
```json
{
  "success": true,
  "project_data": {
    "title": "Kitchen Cabinet Installation",
    "description": "Need to install new kitchen cabinets...",
    "project_type": "Kitchen",
    "location": "New York, NY",
    "budget_min": 5000,
    "budget_max": 8000,
    "timeline": "2-3 weeks"
  }
}
```

### 3.2 Project Detail Screen (`/project/<id>`)
**API Endpoint:** `GET /project/<id>`

**UI Components:**
- Project header (title, status, date)
- Project details card
- Budget and timeline info
- Audio player (if original audio exists)
- Bids section:
  - Bid count indicator
  - Bids list (for homeowners)
  - Submit bid form (for contractors)
- Messages section
- Action buttons (based on user role and project status)

**Homeowner Actions:**
- Accept Bid button
- Reject Bid button
- Close Project button
- Message Contractor button

**Contractor Actions:**
- Submit Bid button
- Edit Bid button (if not accepted)
- Withdraw Bid button
- Message Homeowner button

### 3.3 Review Project Screen (`/review_project`)
**API Endpoint:** `GET /review_project`

**UI Components:**
- AI-generated project preview
- Original audio player
- Transcript display (if available)
- Editable project fields
- "Looks Good" confirmation button
- "Edit Details" button
- "Start Over" button

---

## 4. Bidding System

### 4.1 Submit Bid (`/submit_bid/<project_id>`)
**API Endpoint:** `POST /submit_bid/<project_id>`

**UI Components:**
- Project summary card
- Bid amount input (with currency formatting)
- Timeline input/dropdown
- Work description text area
- Materials/labor breakdown (optional)
- Submit bid button
- Save as draft option

**Request Body:**
```json
{
  "amount": 6500.00,
  "timeline": "3 weeks",
  "description": "I will install your kitchen cabinets with premium materials...",
  "materials_cost": 4000.00,
  "labor_cost": 2500.00
}
```

### 4.2 Bid Management
**API Endpoints:**
- `POST /edit_bid/<bid_id>` (edit bid)
- `POST /withdraw_bid/<bid_id>` (withdraw bid)
- `GET /bid_history/<bid_id>` (bid history)

**UI Components:**
- My Bids list screen
- Bid status indicators
- Edit bid modal
- Withdraw bid confirmation
- Bid history timeline

**Bid Status Types:**
- 📝 Submitted (pending review)
- ✅ Accepted (won the project)
- ❌ Rejected (not selected)
- 🚫 Withdrawn (contractor withdrew)
- ⏰ Expired (time limit exceeded)

---

## 5. Messaging System

### 5.1 Messages Screen (`/contractor/messages`)
**API Endpoints:**
- `GET /api/contractor/messages` (message list)
- `GET /api/bid_messages/<bid_id>` (bid-specific messages)
- `POST /api/bid_messages` (send message)

**UI Components:**
- Conversations list (grouped by project)
- Message thread view
- Message input with send button
- File attachment option
- Message status indicators (sent/delivered/read)
- Real-time message updates

**Message Types:**
- Text messages
- Image attachments
- Document attachments
- System notifications

### 5.2 Notifications (`/api/notifications`)
**API Endpoint:** `GET /api/notifications`

**UI Components:**
- Notification bell icon with badge count
- Notifications dropdown/screen
- Mark as read functionality
- Notification categories:
  - New bids received
  - Bid status updates
  - New messages
  - Project updates
  - System announcements

---

## 6. User Profiles

### 6.1 Contractor Profile (`/contractor/profile`)
**API Endpoints:**
- `GET /contractor/profile` (view profile)
- `POST /contractor/profile/update` (update profile)

**UI Components:**
- Profile photo upload
- Company information
- Specialties selection (multi-select)
- Business description
- Contact information
- Portfolio/work samples
- Reviews and ratings display
- Availability calendar

### 6.2 Contractor Reviews (`/contractor/<id>/reviews`)
**API Endpoint:** `GET /contractor/<id>/reviews`

**UI Components:**
- Overall rating display (stars)
- Reviews list with:
  - Customer name
  - Project type
  - Rating (stars)
  - Review text
  - Date
  - Photos (if any)
- Reply to review option (for contractor)

---

## 7. Admin Features

### 7.1 Admin Dashboard (`/admin`)
**API Endpoint:** `GET /admin`

**UI Components:**
- Platform statistics cards
- Recent activity feed
- Quick action buttons
- Charts and analytics
- System health indicators

### 7.2 User Management (`/admin/users`)
**API Endpoint:** `GET /admin/users`

**UI Components:**
- Users list with search/filter
- User details modal
- Account status toggle
- Role management
- Activity logs

### 7.3 Project Management (`/admin/projects`)
**API Endpoint:** `GET /admin/projects`

**UI Components:**
- Projects list with filters
- Project status management
- Content moderation tools
- Bulk actions

---

## 8. Additional Features

### 8.1 Contact Form (`/contact`)
**API Endpoint:** `POST /contact`

**UI Components:**
- Name input
- Email input
- Subject dropdown
- Message text area
- Submit button
- Contact information display

### 8.2 Audio Testing (`/test_audio`)
**API Endpoint:** `GET /test_audio`

**UI Components:**
- Microphone permission request
- Audio recording test
- Playback test
- Upload test
- Troubleshooting tips

---

## 🎨 UI/UX Design Guidelines

### **Color Scheme**
- Primary Blue: `#1d4ed8`
- Primary Blue Hover: `#1e40af`
- Success Green: `#059669`
- Danger Red: `#dc2626`
- Warning Orange: `#d97706`
- Gray Text: `#64748b`
- Light Gray: `#f1f5f9`

### **Typography**
- Headers: Bold, 18-24px
- Body Text: Regular, 14-16px
- Captions: Regular, 12-14px
- Buttons: Medium weight, 14-16px

### **Component Styling**
- Cards: White background, subtle shadow, rounded corners
- Buttons: Rounded corners (6px), appropriate padding
- Form inputs: Clean borders, focus states
- Status badges: Colored backgrounds with white text

### **Navigation**
- Bottom tab navigation (iOS) / Navigation drawer (Android)
- Consistent header with back button
- Search functionality where applicable
- Floating action button for primary actions

---

## 📱 Platform-Specific Considerations

### **iOS Specific**
- Use UIKit or SwiftUI
- Follow iOS Human Interface Guidelines
- Implement proper navigation stack
- Use iOS-native components (UITableView, UICollectionView)
- Integrate with iOS notifications
- Support dark mode
- Implement proper accessibility features

### **Android Specific**
- Use Material Design components
- Follow Android Design Guidelines
- Implement proper fragment navigation
- Use RecyclerView for lists
- Integrate with Android notifications
- Support different screen sizes
- Implement proper back button handling

---

## 🔧 Technical Implementation Details

### **Data Models**

**User Model:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "homeowner|contractor",
  "is_admin": false,
  "created_at": "2025-01-06T10:00:00Z"
}
```

**Project Model:**
```json
{
  "id": 1,
  "title": "Kitchen Cabinet Installation",
  "description": "Need to install new kitchen cabinets...",
  "project_type": "Kitchen",
  "location": "New York, NY",
  "budget_min": 5000.00,
  "budget_max": 8000.00,
  "timeline": "2-3 weeks",
  "status": "Active|Completed|Closed",
  "homeowner_id": 1,
  "created_at": "2025-01-06T10:00:00Z",
  "bids_count": 5
}
```

**Bid Model:**
```json
{
  "id": 1,
  "amount": 6500.00,
  "timeline": "3 weeks",
  "description": "I will install your kitchen cabinets...",
  "status": "Submitted|Accepted|Rejected|Withdrawn|Expired",
  "project_id": 1,
  "contractor_id": 1,
  "created_at": "2025-01-06T10:00:00Z"
}
```

### **API Response Formats**

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

### **File Upload Handling**
- Support for audio files: MP3, WAV, M4A, AAC
- Support for video files: MP4, MOV, AVI
- Maximum file size: 50MB
- Base64 encoding for API transmission
- Progress indicators for uploads

### **Real-time Features**
- WebSocket connection for real-time messaging
- Push notifications for bid updates
- Live bid count updates
- Real-time message delivery

---

## 🔐 Security Considerations

### **Authentication**
- Secure session management
- Token-based authentication for API calls
- Biometric authentication support (Face ID, Touch ID, Fingerprint)
- Auto-logout after inactivity

### **Data Protection**
- HTTPS for all API communications
- Secure storage of user credentials
- Data encryption at rest
- Privacy controls for user data

### **Permissions**
- Camera access for photo uploads
- Microphone access for audio recording
- Location access for project location
- File system access for uploads
- Push notification permissions

---

## 📊 Analytics & Tracking

### **User Analytics**
- Screen view tracking
- User engagement metrics
- Feature usage statistics
- Conversion funnel analysis

### **Performance Monitoring**
- API response times
- App crash reporting
- Memory usage monitoring
- Battery usage optimization

---

## 🚀 Development Phases

### **Phase 1: Core Features (MVP)**
1. User authentication (login/register)
2. Basic project submission (text-based)
3. Project browsing for contractors
4. Basic bidding system
5. Simple messaging

### **Phase 2: Enhanced Features**
1. Audio recording and AI processing
2. Advanced project management
3. Real-time notifications
4. Enhanced messaging with attachments
5. User profiles and reviews

### **Phase 3: Advanced Features**
1. Admin dashboard
2. Analytics and reporting
3. Advanced search and filtering
4. Video upload support
5. Integration with external services

### **Phase 4: Optimization**
1. Performance optimization
2. Advanced UI/UX improvements
3. Offline functionality
4. Advanced security features
5. Platform-specific optimizations

---

## 📋 Testing Requirements

### **Unit Testing**
- API integration tests
- Data model validation
- Business logic testing
- Error handling verification

### **UI Testing**
- Screen navigation testing
- Form validation testing
- User interaction testing
- Accessibility testing

### **Integration Testing**
- End-to-end user flows
- API communication testing
- File upload/download testing
- Real-time feature testing

---

## 📚 Additional Resources

### **API Documentation**
- Complete endpoint documentation available
- Postman collection for testing
- Sample request/response examples
- Error code reference

### **Design Assets**
- UI mockups and wireframes
- Icon library and assets
- Brand guidelines and colors
- Component library specifications

### **Development Tools**
- Backend API running on EC2
- Database schema documentation
- Development environment setup
- Testing data and scenarios

---

**Document Version:** 1.0  
**Last Updated:** January 6, 2025  
**Contact:** Development Team  

This specification provides a comprehensive foundation for developing mobile applications that fully replicate the HomePro web platform functionality. The mobile apps should maintain feature parity while optimizing for mobile-specific user experiences and platform conventions.