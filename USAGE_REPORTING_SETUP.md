# Usage Reporting Setup Guide

## Overview

This guide explains how to set up and configure users with reporting capabilities for the usage tracking system. The usage reporting feature provides detailed analytics on system usage, including operations performed, LLM model usage, storage consumption, and more.

## Prerequisites

Before setting up reporting users, ensure that:
1. The usage tracking database tables have been created (migration 003)
2. The background jobs for aggregation are running (optional but recommended for complete data)

## Setting Up a Reporting User

### Method 1: Direct Database Update (Admin Required)

For administrators, you can directly assign the reporting role to an existing user by updating the `accounts` table:

```sql
UPDATE accounts 
SET roles = roles || '{reporting}' 
WHERE email = 'user@example.com';
```

Or if you want to assign multiple roles:

```sql
UPDATE accounts 
SET roles = '{"admin", "reporting"}' 
WHERE email = 'user@example.com';
```

### Method 2: Through the API (Admin Required)

You can also update user roles programmatically using the API:

```bash
curl -X PUT \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "roles": ["reporting"]
  }' \
  "http://your-domain.com/account/update"
```

### Method 3: Using the Admin Panel (When Available)

If your system has an admin panel with user management capabilities, you can assign the reporting role through the UI.

## Verifying the Setup

After assigning the reporting role, the user should be able to:

1. See the "Usage Reporting" tab in the main navigation
2. Access the reporting dashboard
3. View usage statistics filtered by their account
4. Access detailed reports and export functionality

## Role Permissions

The "reporting" role grants the following permissions:
- Access to the usage reporting dashboard
- Ability to view usage statistics for their account
- Ability to export usage data as CSV
- Access to detailed event logs within their account scope

Users with the "admin" role automatically have reporting permissions as well.

## Troubleshooting

### Issue: Reporting Tab Not Visible
- Verify the user has the "reporting" role assigned in their account
- Check that the JWT token contains the correct roles
- Clear browser cache and refresh the page

### Issue: Access Denied to Reports
- Confirm the user has the "reporting" role in the accounts table
- Ensure the JWT token is properly formatted with roles
- Check server logs for authentication errors

### Issue: Empty Reports
- Verify that usage tracking is properly configured and running
- Check that the background aggregation jobs are running (typically daily at 2 AM)
- Ensure sufficient time has passed for data to be collected and aggregated

## Background Jobs

The usage tracking system relies on two daily background jobs:

1. **Daily Usage Aggregation** (runs at 2:00 AM daily)
   - Aggregates individual usage events into daily summaries
   - Populates the `usage_summaries` table

2. **Daily Storage Calculation** (runs at 3:00 AM daily)
   - Calculates storage usage per account
   - Updates the `storage_usage` table

Make sure these jobs are running properly for complete reporting data.

## Security Notes

- The reporting role only allows access to data within the user's account scope
- Users cannot view usage data for other accounts
- API endpoints are protected by JWT authentication
- All usage events are logged with source type (workbench vs API) and IP address