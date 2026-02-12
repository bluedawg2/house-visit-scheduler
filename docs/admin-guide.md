# Admin Guide -- House Visit Scheduler

## Accessing the Admin Dashboard

Go to your app URL with `/admin` at the end:

```
https://your-app.streamlit.app/admin
```

Bookmark this link for easy access. This page is not visible to visitors.

---

## Dashboard Overview

The admin dashboard has two main sections:

1. **Calendar Overview** -- Always visible at the top. Shows all availability and bookings at a glance.
2. **Tabs** -- Four tabs below the calendar for managing different aspects.

### Calendar Color Guide

| Color  | Meaning                           |
|--------|-----------------------------------|
| Green  | Available dates                   |
| Orange | Pending request (waiting for you) |
| Blue   | Accepted booking                  |

---

## Tabs

### Requests Tab

This is the default tab and shows all pending visit requests.

Each request shows:
- Guest name and email
- Requested dates
- Any notes from the guest
- When it was submitted

**To accept a request:**
1. Optionally type a note in the "Add a note..." field
2. Click **"Accept"**
3. The guest receives a confirmation email with a calendar invite
4. You receive a calendar invite in your Google Calendar

**To reject a request:**
1. Optionally type a note explaining why (the guest will see this)
2. Click **"Reject"**
3. The guest receives an email letting them know

When there are no pending requests, you'll see "No pending requests. You're all caught up!"

The tab label shows the count of pending requests (e.g., "Requests (3)").

---

### Availability Tab

This is where you control which dates visitors can book.

**Adding available dates:**
1. Set the **"From"** date (start of availability)
2. Set the **"To"** date (end of availability)
3. Click **"Add Availability"**
4. The calendar above will update to show the new green dates

**Removing available dates:**
- Each availability range is listed on the right with a **"Remove"** button
- Clicking Remove will delete that availability window
- Any pending requests that no longer fall within available dates will be automatically rejected

---

### History Tab

View all past and current requests in one place.

**Filtering:**
- **Filter by status** -- Show All, Pending, Accepted, or Rejected requests
- **Search** -- Type a name or email to find specific requests

Each request shows the guest name, email, dates, status badge, and any notes.

---

### Settings Tab

#### Your Gmail

Enter the Gmail address where you want to receive notifications.

1. Type your Gmail address
2. Click **"Save"**

You will receive:
- An email when a guest submits a new request
- A Google Calendar invite when you accept a booking

#### Booking Rules

Set limits on how long guests can stay:

- **Minimum nights** -- Guests must book at least this many nights (default: 1)
- **Maximum nights** -- The longest stay allowed (set to 0 for no limit)

Click **"Save Rules"** after making changes. These rules are enforced automatically when visitors try to book.

---

## Sharing With Visitors

Your visitor booking page is the root URL of your app:

```
https://your-app.streamlit.app
```

Send this link to anyone you'd like to invite. They'll see the booking calendar and can submit a visit request. They do not need to log in or create an account.

---

## Quick Reference

| Task                    | Where                          |
|-------------------------|--------------------------------|
| See all bookings        | Calendar at the top            |
| Review pending requests | Requests tab                   |
| Accept/reject a request | Requests tab > Accept / Reject |
| Add available dates     | Availability tab               |
| Remove available dates  | Availability tab > Remove      |
| Search past requests    | History tab                    |
| Set your email          | Settings tab > Your Gmail      |
| Set stay limits         | Settings tab > Booking Rules   |
