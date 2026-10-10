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
        {'owner': 'H', 'status': 'open'},
        {'owner': 'H', 'status': 'processing'},
        {'owner': 'I', 'status': 'closed'},
        {'owner': 'J', 'status': 'unknown'},
        {'owner': 'J', 'status': 'closed'},
        {'owner': 'K', 'status': 'unknown'},
        {'owner': 'L', 'status': 'open'},
        {'owner': 'M', 'status': 'processing'},
        {'owner': 'M', 'status': 'closed'},
        {'owner': 'N', 'status': 'unknown'},
        {'owner': 'O', 'status': 'open'},
        {'owner': 'O', 'status': 'processing'},
        {'owner': 'P', 'status': 'closed'},
        {'owner': 'Q', 'status': 'unknown'},
        {'owner': 'R', 'status': 'open'},
        {'owner': 'S', 'status': 'processing'},
        {'owner': 'T', 'status': 'closed'},
        {'owner': 'U', 'status': 'unknown'},
        {'owner': 'V', 'status': 'open'},
        {'owner': 'W', 'status': 'processing'},
        {'owner': 'X', 'status': 'closed'},
        {'owner': 'Y', 'status': 'unknown'},
        {'owner': 'Z', 'status': 'open'},
        {'owner': 'Z', 'status': 'processing'},
        {'owner': 'Z', 'status': 'closed'},
    ]
    expected = {
        'A': {'total': 2, 'open': 1, 'processing': 1, 'closed': 0, 'other': 0},
        'B': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'C': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'D': {'total': 2, 'open': 1, 'processing': 0, 'closed': 0, 'other': 1},
        'E': {'total': 2, 'open': 0, 'processing': 0, 'closed': 2, 'other': 0},
        'F': {'total': 2, 'open': 0, 'processing': 1, 'closed': 1, 'other': 0},
        'G': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'H': {'total': 2, 'open': 1, 'processing': 1, 'closed': 0, 'other': 0},
        'I': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'J': {'total': 2, 'open': 0, 'processing': 0, 'closed': 2, 'other': 0},
        'K': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'L': {'total': 1, 'open': 1, 'processing': 0, 'closed': 0, 'other': 0},
        'M': {'total': 2, 'open': 0, 'processing': 1, 'closed': 1, 'other': 0},
        'N': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'O': {'total': 2, 'open': 1, 'processing': 1, 'closed': 0, 'other': 0},
        'P': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'Q': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'R': {'total': 1, 'open': 1, 'processing': 0, 'closed': 0, 'other': 0},
        'S': {'total': 1, 'open': 0, 'processing': 1, 'closed': 0, 'other': 0},
        'T': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'U': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'V': {'total': 1, 'open': 1, 'processing': 0, 'closed': 0, 'other': 0},
        'W': {'total': 1, 'open': 0, 'processing': 1, 'closed': 0, 'other': 0},
        'X': {'total': 1, 'open': 0, 'processing': 0, 'closed': 1, 'other': 0},
        'Y': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'Z': {'total': 3, 'open': 1, 'processing': 1, 'closed': 1, 'other': 0},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 4: Mixed status and owner
    records = [
        {'owner': 'A', 'status': 'Open'},
        {'owner': 'A', 'status': 'processing'},
        {'owner': 'A', 'status': 'closed'},
        {'owner': 'A', 'status': 'unknown'},
        {'owner': 'B', 'status': 'open'},
        {'owner': 'B', 'status': 'unknown'},
        {'owner': 'C', 'status': 'processing'},
        {'owner': 'C', 'status': 'closed'},
        {'owner': 'D', 'status': 'unknown'},
        {'owner': 'E', 'status': 'unknown'},
        {'owner': 'F', 'status': 'unknown'},
        {'owner': 'G', 'status': 'unknown'},
        {'owner': 'H', 'status': 'unknown'},
        {'owner': 'I', 'status': 'unknown'},
        {'owner': 'J', 'status': 'unknown'},
        {'owner': 'K', 'status': 'unknown'},
        {'owner': 'L', 'status': 'unknown'},
        {'owner': 'M', 'status': 'unknown'},
        {'owner': 'N', 'status': 'unknown'},
        {'owner': 'O', 'status': 'unknown'},
        {'owner': 'P', 'status': 'unknown'},
        {'owner': 'Q', 'status': 'unknown'},
        {'owner': 'R', 'status': 'unknown'},
        {'owner': 'S', 'status': 'unknown'},
        {'owner': 'T', 'status': 'unknown'},
        {'owner': 'U', 'status': 'unknown'},
        {'owner': 'V', 'status': 'unknown'},
        {'owner': 'W', 'status': 'unknown'},
        {'owner': 'X', 'status': 'unknown'},
        {'owner': 'Y', 'status': 'unknown'},
        {'owner': 'Z', 'status': 'unknown'},
    ]
    expected = {
        'A': {'total': 4, 'open': 1, 'processing': 1, 'closed': 1, 'other': 1},
        'B': {'total': 2, 'open': 1, 'processing': 0, 'closed': 0, 'other': 1},
        'C': {'total': 2, 'open': 0, 'processing': 1, 'closed': 1, 'other': 0},
        'D': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'E': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'F': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'G': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'H': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'I': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'J': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'K': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'L': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'M': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'N': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'O': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'P': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'Q': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'R': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'S': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'T': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'U': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'V': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'W': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'X': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'Y': {'total': 1, 'open': 0, 'processing': 0, 'closed': 0, 'other': 1},
        'unassigned': {'total': 0, 'open': 0, 'processing': 0, 'closed': 0, 'other': 0}
    }
    assert aggregate_by_owner(records) == expected
    
    # Test 5: All unassigned and unknown status
    records = [
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
        {'owner': None, 'status': 'unknown'},
    ]
    expected = {
        'unassigned': {'total': 5, 'open': 0, 'processing': 0, 'closed': 0, 'other': 5}
    }
    assert aggregate_by_owner(records) == expected

    print("All test cases passed.")
