# Usage tracking and administrative reporting

Implement tracking in the database to track each use account's
use of the system by time, Workbench vs. API usage, and by
what LLM is used. This is necessary to correctly bill users
based on the cost of the specific model used for each fact
extraction task.

The feature is available to all users to view their own usage history.
Users with the `reporting` role can also view the usage history of all users.

## Usage tracking

- Totals for each day
- Usage by model tracked
- Tracked for each user
- Daily total for the amount of physical/object-store storage the user's documents are using

## Reporting administrative users

Create a user role for reporting. The REST API needs to have an extension that the reporting
role can access can use to retrieve the usage data. All users can see their own usage. The
reporting role can see the aggregate usage across all users, and sees the user sector to
see the breakdown by user.

### Reporting workbench features

- Graph of usages
- Select specific uses
- Select timeframe for report
- Breakdown by model use
- Download the report as CSV