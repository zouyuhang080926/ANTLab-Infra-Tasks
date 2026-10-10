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
        {'owner': 'F', 'status': 'closed'},
        {'owner': 'G', 'status': 'unknown'},
        {'owner': 'H', 'status': 'unknown'},
        {'owner': 'I', 'status': 'closed'},
        {'owner': 'J', 'status': 'unknown'},
        {'owner': 'K', 'status': 'open'},
        {'owner': 'L', 'status': 'processing'},
        {'owner': 'M', 'status': 'closed'},
        {'owner': 'N', 'status': 'unknown'},
        {'owner': 'O', 'status': 'unknown'},
        {'owner': 'P', 'status': 'closed'},
    ]
    expected = {
        'A': {'total': 2, 'open': 1, 'processing': 1, 'closed': 0, 'other': 0},
        'B': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'C': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'D': {'total': 2, 'open': 1, 'processing': 0, 'closed': 0, 'other': 1},
        'E': {'total': 2, 'open': 0, 'processing': 0, 'closed': 2, 'other': 0},
        'F': {'total': 2, 'open': 0, 'processing': 1, 'closed': 1, 'other': 0},
        'G': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'H': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'I': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'J': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'K': {'total': 1, 'open': 1, 'processing': 0, 'closed': 0, 'other': 0},
        'L': {'total': 1, 'open': 0, 'processing': 1, 'closed': 0, 'other': 0},
        'M': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'N': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'O': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'P': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 4: Multiple records with unassigned owner
    records = [
        {'owner': None, 'status': 'open'},
        {'owner': None, 'status': 'processing'},
        {'owner': None, 'status': 'closed'},
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
    ]
    expected = {
        'unassigned': {'total': 6, 'open': 1, 'processing': 1, 'closed': 1, 'other': 3}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 5: Mixed statuses and owners
    records = [
        {'owner': 'A', 'status': 'open'},
        {'owner': 'A', 'status': 'unknown'},
        {'owner': 'A', 'status': 'processing'},
        {'owner': 'B', 'status': 'closed'},
        {'owner': 'C', 'status': 'unknown'},
        {'owner': 'D', 'status': 'unknown'},
        {'owner': 'E', 'status': 'closed'},
        {'owner': 'F', 'status': 'unknown'},
        {'owner': 'G', 'status': 'open'},
        {'owner': 'H', 'status': 'unknown'},
        {'owner': 'I', 'status': 'closed'},
        {'owner': 'J', 'status': 'unknown'},
        {'owner': 'K', 'status': 'unknown'},
        {'owner': 'L', 'status': 'unknown'},
        {'owner': 'M', 'status': 'unknown'},
        {'owner': 'N', 'status': 'unknown'},
        {'owner': 'O', 'status': 'unknown'},
        {'owner': 'P', 'status': 'unknown'},
        {'owner': 'Q', 'status': 'unknown'},
        {'owner': 'R', 'status': 'unknown'},
    ]
    expected = {
        'A': {'total': 3, 'open': 1, 'processing': 1, 'closed': 0, 'other': 1},
        'B': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'C': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'D': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'E': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'F': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'G': {'total': 1, 'open': 1, 'processing': 0, 'closed': 0, 'other': 0},
        'H': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'I': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'J': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'K': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'L': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'M': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'N': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'O': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'P': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'Q': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'R': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    print("All test cases passed.")
