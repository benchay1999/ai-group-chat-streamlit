# MTurk XML Parsing Error Fix

## Date: October 31, 2025

## Error Encountered

```
Failed to create HIT: An error occurred (ParameterValidationError) 
when calling the CreateHIT operation: There was an error parsing the XML 
question or answer data in your request. Please make sure the data is 
well-formed and validates against the appropriate schema. Details: 
The reference to entity "tx" must end with the ';' delimiter.
```

## Root Cause

The external URL used in the MTurk HIT contains query parameters with `&` characters:

```python
# In per_transaction_hit_service.py
cashout_confirm_url = f"{base_url}/cashout-confirm?code={transaction.redemption_code}&tx={transaction.id}"
```

Example URL:
```
https://ai-group-chat.netlify.app/cashout-confirm?code=abc123&tx=uuid-456
```

When this URL is inserted into XML:
```xml
<ExternalURL>https://example.com?code=abc&tx=123</ExternalURL>
```

**The `&` character is treated as an XML entity reference**, causing the parser to expect `;` after `tx` (like `&lt;` or `&gt;`).

In XML, the `&` character **must be escaped as `&amp;`**.

## The Fix

**File**: `backend/mturk_api.py`  
**Lines**: 442-451

### Before (BROKEN):
```python
# Build ExternalQuestion XML for cashout confirmation page
external_question = f"""<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>{external_url}</ExternalURL>
  <FrameHeight>{self.frame_height}</FrameHeight>
</ExternalQuestion>"""
```

### After (FIXED):
```python
# Build ExternalQuestion XML for cashout confirmation page
# Important: Escape XML special characters in URL (& becomes &amp;)
import xml.sax.saxutils as saxutils
escaped_url = saxutils.escape(external_url)

external_question = f"""<?xml version="1.0" encoding="UTF-8"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
  <ExternalURL>{escaped_url}</ExternalURL>
  <FrameHeight>{self.frame_height}</FrameHeight>
</ExternalQuestion>"""
```

## How `saxutils.escape()` Works

The `xml.sax.saxutils.escape()` function escapes XML special characters:

| Character | Escaped As | Purpose |
|-----------|------------|---------|
| `&` | `&amp;` | Entity reference |
| `<` | `&lt;` | Tag start |
| `>` | `&gt;` | Tag end |
| `"` | `&quot;` | Attribute quote (optional) |
| `'` | `&apos;` | Attribute quote (optional) |

### Example:
```python
import xml.sax.saxutils as saxutils

url = "https://example.com?code=abc&tx=123"
escaped = saxutils.escape(url)

print(escaped)
# Output: https://example.com?code=abc&amp;tx=123
```

## Result

### Before (Invalid XML):
```xml
<ExternalURL>https://example.com/cashout-confirm?code=abc123&tx=uuid-456</ExternalURL>
```
❌ Parser error: `&tx` is interpreted as entity reference

### After (Valid XML):
```xml
<ExternalURL>https://example.com/cashout-confirm?code=abc123&amp;tx=uuid-456</ExternalURL>
```
✅ Parser accepts: `&amp;` is valid entity reference for `&`

### Browser Behavior:
When MTurk renders the HIT, the browser automatically converts `&amp;` back to `&` in the URL, so the final URL works correctly:
```
https://example.com/cashout-confirm?code=abc123&tx=uuid-456
```

## Why This Matters

MTurk's `CreateHIT` API validates the XML structure before accepting the HIT creation request. Invalid XML causes immediate rejection with a `ParameterValidationError`.

This is a **critical fix** because:
1. ✅ Every cashout creates a URL with query parameters
2. ✅ Query parameters use `&` as separators
3. ✅ Without escaping, **all cashout requests would fail**

## Testing

### Test the Escaping:
```python
import xml.sax.saxutils as saxutils

# Test URL with multiple query params
url = "https://ai-group-chat.netlify.app/cashout-confirm?code=a1b2c3&tx=uuid-123-456"
escaped = saxutils.escape(url)

print("Original:", url)
print("Escaped: ", escaped)

# Output:
# Original: https://ai-group-chat.netlify.app/cashout-confirm?code=a1b2c3&tx=uuid-123-456
# Escaped:  https://ai-group-chat.netlify.app/cashout-confirm?code=a1b2c3&amp;tx=uuid-123-456
```

### Expected Result After Fix:
1. ✅ HIT creation succeeds
2. ✅ XML validates correctly
3. ✅ Worker can access the HIT
4. ✅ Clicking the HIT loads the correct URL (browser un-escapes `&amp;` to `&`)

## Related Files

- **Fixed**: `backend/mturk_api.py` (lines 442-451)
- **Uses**: `backend/per_transaction_hit_service.py` (creates URLs with query params)
- **Endpoint**: `backend/cashout_endpoint_v2.py` (V2 cashout system)

## XML Standards Reference

From [W3C XML Specification](https://www.w3.org/TR/xml/#sec-predefined-ent):

> The ampersand character (&) and the left angle bracket (<) MUST NOT appear in their literal form, except when used as markup delimiters. If they are needed elsewhere, they must be escaped using either numeric character references or the strings "&amp;" and "&lt;" respectively.

## Next Steps

1. ✅ Fix applied
2. ✅ Syntax validated
3. 🔄 Restart backend server
4. 🧪 Test cashout again - should now work!

---

**Status**: ✅ FIXED  
**Tested**: Escaping verified  
**Impact**: Critical fix - enables all cashout transactions  

