# Lessons Learned

## 2026-02-06: Earnings Date Selection Logic

### Issue
When fixing the earnings date selection to prioritize reported earnings over future dates, the initial fix only handled events with `actual_eps` populated. This missed the case where a company reported earnings (e.g., yesterday) but Finnhub's API hadn't updated the actual results yet.

### Root Cause
The fix had a gap in the selection logic:
- Captured: Past events WITH actual_eps
- Captured: Future events WITHOUT actual_eps
- **Missed**: Past events WITHOUT actual_eps (earnings happened but API results pending)

### Lesson
When dealing with external API data that may have delayed updates, always account for the "data pending" state. Don't assume that if an event occurred, the results will be immediately available. Design selection logic to handle:
1. Confirmed state (data available)
2. Pending state (event occurred, data not yet available)
3. Future state (event hasn't occurred yet)

### Fix Applied
Changed the priority order to:
1. Past events with actual_eps (confirmed reported)
2. Past events without actual_eps (reported but results pending in API)
3. Nearest upcoming/future earnings (fallback)
