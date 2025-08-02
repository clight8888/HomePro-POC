# HomePro Admin Portal & Business Intelligence

This document provides comprehensive information about the HomePro Admin Portal and Business Intelligence system.

## Overview

The Admin Portal provides comprehensive platform management capabilities including:

- **Admin Dashboard**: Real-time platform statistics and KPIs
- **User Management**: Complete user account management and verification workflows
- **Project Management**: Project lifecycle monitoring and approval workflows
- **Business Intelligence**: Advanced analytics and reporting
- **Content Moderation**: Content review and moderation tools

## Features

### 1. Admin Dashboard
- Real-time platform statistics (users, projects, revenue)
- Key performance indicators (KPIs) dashboard
- Activity timeline and alerts
- System health monitoring
- Quick action links

### 2. User Management System
- User account management (homeowners & contractors)
- User verification and approval workflow
- Account suspension/activation controls
- User activity logs and audit trails
- Admin user creation and management

### 3. Project Lifecycle Management
- Project status monitoring across all stages
- Project approval/rejection workflow
- Dispute resolution management
- Project completion verification
- Project analytics and insights

### 4. Business Intelligence & Analytics
- Revenue tracking and financial reports
- User engagement analytics
- Project success rate metrics
- Contractor performance analytics
- Geographic distribution reports
- Seasonal trend analysis

### 5. Content Moderation
- Review and approve contractor profiles
- Monitor project descriptions and images
- Flag inappropriate content
- Manage user-reported issues
- Moderation history and audit trails

## Database Schema

### Admin Tables

#### admin_users
- `id`: Primary key
- `user_id`: Foreign key to users table
- `admin_level`: Admin access level (super_admin, admin, moderator)
- `permissions`: JSON string of specific permissions
- `created_by`: Admin who created this admin user
- `created_at`: Creation timestamp
- `is_active`: Admin account status

#### admin_activity_logs
- `id`: Primary key
- `admin_id`: Foreign key to admin_users
- `action`: Action performed
- `target_type`: Type of target (user, project, etc.)
- `target_id`: ID of the target
- `details`: Additional details about the action
- `ip_address`: IP address of the admin
- `created_at`: Action timestamp

#### system_metrics
- `id`: Primary key
- `metric_name`: Name of the metric
- `metric_value`: Numeric value
- `metric_date`: Date for the metric
- `created_at`: Record creation timestamp

#### user_verification
- `id`: Primary key
- `user_id`: Foreign key to users table
- `verification_type`: Type of verification (license, insurance, etc.)
- `status`: Verification status (pending, approved, rejected)
- `submitted_at`: Submission timestamp
- `reviewed_at`: Review timestamp
- `reviewed_by`: Admin who reviewed
- `documents`: JSON string of document references
- `notes`: Review notes

#### content_moderation
- `id`: Primary key
- `content_type`: Type of content (project, profile, bid, review)
- `content_id`: ID of the content
- `reported_by`: User who reported the content
- `reason`: Reason for reporting
- `status`: Moderation status (pending, approved, rejected)
- `reviewed_by`: Admin who reviewed
- `reviewed_at`: Review timestamp
- `notes`: Moderation notes
- `created_at`: Report timestamp

## Setup Instructions

### 1. Initialize Database
The admin tables are automatically created when the application starts. The `init_database()` function in `app.py` handles this.

### 2. Create First Admin User
Run the setup script to create the first admin user:

```bash
python setup_admin.py
```

This will prompt you for:
- Admin email
- First name
- Last name
- Password

The first admin user will be created with `super_admin` level access.

### 3. Generate Sample Data (Optional)
For testing purposes, you can generate sample data:

```bash
python generate_sample_data.py
```

This creates:
- 10 homeowners and 10 contractors
- 25 sample projects
- Multiple bids per project
- 30 days of system metrics
- Sample verification requests
- Sample content moderation items

## Admin Access Levels

### Super Admin
- Full access to all admin features
- Can create/manage other admin users
- Can access all analytics and reports
- Can perform all moderation actions

### Admin
- Access to most admin features
- Cannot create other admin users
- Can access analytics and reports
- Can perform moderation actions

### Moderator
- Limited access focused on content moderation
- Can review and moderate content
- Can view basic analytics
- Cannot manage users or create admins

## API Endpoints

### Admin Dashboard
- `GET /admin` - Admin dashboard overview
- `GET /admin/users` - User management interface
- `GET /admin/projects` - Project management interface
- `GET /admin/analytics` - Business intelligence dashboard
- `GET /admin/moderation` - Content moderation interface

### Admin Actions
- `POST /admin/user/<int:user_id>/toggle_status` - Toggle user active status
- `POST /admin/create_admin` - Create new admin user
- `POST /admin/verify_user/<int:verification_id>` - Approve/reject user verification
- `POST /admin/moderate_content/<int:moderation_id>` - Moderate content

## Security Features

### Authentication
- Admin access requires both user authentication and admin privileges
- Admin actions are logged with IP addresses and timestamps
- Session management with secure cookies

### Authorization
- Role-based access control with different admin levels
- Permission checking for sensitive operations
- Audit trails for all admin actions

### Data Protection
- Sensitive data is properly sanitized
- SQL injection protection through parameterized queries
- XSS protection in templates

## Analytics & Reporting

### User Analytics
- User registration trends
- User engagement metrics
- User retention rates
- Geographic distribution

### Project Analytics
- Project creation trends
- Project completion rates
- Average project values
- Project type distribution

### Financial Analytics
- Revenue tracking
- Commission calculations
- Payment processing metrics
- Financial forecasting

### Performance Metrics
- Platform response times
- Error rates
- System availability
- Database performance

## Monitoring & Alerts

### System Health
- Database connection monitoring
- Application performance metrics
- Error rate tracking
- Resource utilization

### Business Metrics
- Daily active users
- Project completion rates
- Revenue targets
- User satisfaction scores

### Alert Thresholds
- High error rates
- Low user engagement
- System performance issues
- Security incidents

## Best Practices

### Admin User Management
1. Use strong passwords for admin accounts
2. Regularly review admin access levels
3. Remove inactive admin users
4. Monitor admin activity logs

### Content Moderation
1. Review reported content promptly
2. Document moderation decisions
3. Maintain consistent moderation standards
4. Escalate complex cases to senior admins

### Data Management
1. Regular database backups
2. Monitor system metrics
3. Archive old data appropriately
4. Maintain data privacy compliance

### Security
1. Regular security audits
2. Keep admin access logs
3. Monitor for suspicious activity
4. Update security measures regularly

## Troubleshooting

### Common Issues

#### Admin Login Issues
- Verify user has `is_admin = 1` in database
- Check admin_users table for admin record
- Verify session is properly authenticated

#### Permission Errors
- Check admin_level in admin_users table
- Verify required permissions for action
- Review admin activity logs for errors

#### Data Display Issues
- Check database connections
- Verify table schemas are up to date
- Review application logs for errors

### Support
For technical support or questions about the admin portal, please refer to the main application documentation or contact the development team.

## Future Enhancements

### Planned Features
- Advanced reporting with custom date ranges
- Email notifications for admin alerts
- Bulk user management operations
- Advanced analytics with machine learning insights
- Mobile admin interface
- Integration with external business intelligence tools

### Performance Improvements
- Database query optimization
- Caching for frequently accessed data
- Asynchronous processing for heavy operations
- Real-time updates using WebSockets