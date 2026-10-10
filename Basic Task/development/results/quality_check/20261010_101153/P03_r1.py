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
        if status in ['open', 'processing', 'closed']:
            result[owner][status] += 1
        else:
            result[owner]['other'] += 1
    
    # Convert defaultdict to regular dict
    return dict(result)

# Test cases
def test_aggregate_by_owner():
    # Test 1: Empty input
    assert aggregate_by_owner([]) == {}
    
    # Test 2: One record with unassigned owner and unknown status
    assert aggregate_by_owner([{'owner': None, 'status': 'unknown'}]) == {
        'unassigned': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1}
    }
    
    # Test 3: Multiple records with different owners and statuses
    records = [
        {'owner': 'A', 'status': 'open'},
        {'owner': 'A', 'status': 'processing'},
        {'owner': 'B', 'status': 'closed'},
        {'owner': 'C', 'status': 'unknown'},
        {'owner': 'D', 'status': 'open'},
        {'owner': 'D', 'status': 'unknown'},
        {'owner': 'E', 'status': 'closed'},
        {'owner': 'E', 'status': 'unknown'},
        {'owner': 'F', 'status': 'processing'},
        {'owner': 'F', 'status': 'unknown'},
    ]
    expected = {
        'A': {'total': 2, 'open': 1, 'processing': 1, 'closed': 0, 'other': 0},
        'B': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'C': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'D': {'total': 2, 'open': 1, 'processing': 0, 'closed': 0, 'other': 1},
        'E': {'total': 2, 'open': 0, 'processing': 0, 'closed': 1, 'other': 1},
        'F': {'total': 2, 'open': 0, 'processing': 1, 'closed': 0, 'other': 1},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 4: Mixed case status
    records = [
        {'owner': 'A', 'status': 'Open'},
        {'owner': 'A', 'status': 'Processing'},
        {'owner': 'A', 'status': 'Closed'},
        {'owner': 'A', 'status': 'unknown'},
        {'owner': 'B', 'status': 'open'},
        {'owner': 'B', 'status': 'Processing'},
        {'owner': 'B', 'status': 'Closed'},
        {'owner': 'B', 'status': 'Unknown'},
    ]
    expected = {
        'A': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1},
        'B': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 5: Owner is None and status is unknown
    records = [
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'Unknown'},
        {'owner': None, 'status': 'OPEN'},
        {'owner': None, 'status': 'processing'},
        {'owner': None, 'status': 'closed'},
    ]
    expected = {
        'unassigned': {'total': 5, 'open': 1, 'processing': 1, 'closed': 1, 'other': 2}
    }
    assert aggregate_by_owner(records) == expected
    
    print("All test cases passed.")
