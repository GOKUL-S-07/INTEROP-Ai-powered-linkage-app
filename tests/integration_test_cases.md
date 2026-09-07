# Integration & Testing

## Integration Flow

Citizen → Frontend → REST API → Backend → Database + ML → Government Services → Status Dashboard

## Test Cases

| Test ID | Test Case | Expected Result |
|---|---|---|
| TC01 | Frontend sends request to Backend | Request received successfully |
| TC02 | Backend stores data in Database | Data stored correctly |
| TC03 | Backend communicates with ML module | ML response received correctly |
| TC04 | Government service API communication | Request and response handled correctly |
| TC05 | Invalid input validation | Proper error message displayed |
| TC06 | Application status synchronization | Updated status shown on dashboard |
| TC07 | Complete end-to-end workflow | Request reaches final status successfully |
| TC08 | API/server failure | Error handled without system crash |
