from collections import defaultdict

def aggregate_by_owner(records):
    result = defaultdict(lambda: {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0})
    
    for record in records:
        owner = record.get('owner', 'unassigned')
        status = record.get('status', '').lower()
        
        # Handle owner
        if owner != 'unassigned':
            result[owner]['total'] += 1
        else:
            result['unassigned']['total'] += 1
        
        # Handle status
        if status == 'open':
            result[owner]['open'] += 1
        elif status == 'processing':
            result[owner]['processing'] += 1
        elif status == 'closed':
            result[owner]['closed'] += 1
        else:
            result[owner]['other'] += 1
    
    # Convert defaultdict to regular dict
    return dict(result)

# Test cases
def test_aggregate_by_owner():
    # Test 1: Empty input
    assert aggregate_by_owner([]) == {}
    
    # Test 2: All records have owner and status
    records = [
        {'owner': 'A', 'status': 'open'},
        {'owner': 'A', 'status': 'processing'},
        {'owner': 'A', 'status': 'closed'},
        {'owner': 'A', 'status': 'other'},
        {'owner': 'B', 'status': 'open'},
        {'owner': 'B', 'status': 'processing'},
        {'owner': 'B', 'status': 'closed'},
        {'owner': 'B', 'status': 'other'},
    ]
    expected = {
        'A': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1},
        'B': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 3: Missing owner
    records = [
        {'status': 'open'},
        {'status': 'processing'},
        {'status': 'closed'},
        {'status': 'other'},
    ]
    expected = {
        'unassigned': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 4: Mixed status and owner
    records = [
        {'owner': 'A', 'status': 'Open'},
        {'owner': 'A', 'status': 'Processing'},
        {'owner': 'A', 'status': 'Closed'},
        {'owner': 'A', 'status': 'Other'},
        {'owner': 'B', 'status': 'open'},
        {'owner': 'B', 'status': 'Processing'},
        {'owner': 'B', 'status': 'Closed'},
        {'owner': 'B', 'status': 'Other'},
    ]
    expected = {
        'A': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1},
        'B': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 5: All records have unassigned owner
    records = [
        {'status': 'open'},
        {'status': 'processing'},
        {'status': 'closed'},
        {'status': 'other'},
    ]
    expected = {
        'unassigned': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1}
    }
    assert aggregate_by_owner(records) == expected
    
    print("All test cases passed.")

test_aggregate_by_owner()
