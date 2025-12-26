# User API Examples

This directory contains example scripts for using the QuantumExecute User APIs.

## Exchange API Management

- `list_exchange_apis.py` - List all configured exchange API keys
- `add_exchange_api.py` - Add a new exchange API key

## Trading Operations

- `get_master_orders.py` - Query master orders with various filters
- `get_order_fills.py` - Get order execution details and fills
- `create_master_order.py` - Create new algorithmic orders (TWAP, VWAP, etc.)
- `cancel_master_order.py` - Cancel active master orders
- `get_tca_analysis.py` - Get TCA (Transaction Cost Analysis) data with various filters

## Prerequisites

1. Set up your API credentials in environment variables or config file
2. Install the qe-connector-python package
3. Run any example:
   ```bash
   python examples/user/list_exchange_apis.py
   ```

## Error Handling

All examples include proper error handling for:
- `APIError` - Server-side errors with error codes
- `ClientError` - Client-side errors (network, validation, etc.)

## Response Format

All API responses follow a consistent format:
```python
{
    "code": 200,  # Success code
    "message": {...},  # Actual response data
    "reason": "OK",
    "traceId": "xxx",
    "serverTime": 1234567890
}
```

The SDK automatically extracts the `message` field when `code` is 200.
