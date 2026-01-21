"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Fixture to provide a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Fixture to reset activities to initial state"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    # Import activities dict to reset it
    from app import activities
    
    # Reset
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Cleanup
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test that we can retrieve all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Check activity details
        assert data["Chess Club"]["description"] == "Learn strategies and compete in chess tournaments"
        assert data["Chess Club"]["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert data["Chess Club"]["max_participants"] == 12
        assert len(data["Chess Club"]["participants"]) == 2
    
    def test_get_activities_has_participants(self, client, reset_activities):
        """Test that activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]


class TestSignUpForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistent%20Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_registration(self, client, reset_activities):
        """Test that duplicate signup returns 400"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test that multiple students can sign up for same activity"""
        # Sign up first student
        response1 = client.post(
            "/activities/Programming%20Class/signup?email=alice@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Sign up second student
        response2 = client.post(
            "/activities/Programming%20Class/signup?email=bob@mergington.edu"
        )
        assert response2.status_code == 200
        
        # Verify both are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()["Programming Class"]["participants"]
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/NonExistent%20Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_registered_student(self, client, reset_activities):
        """Test unregister when student is not registered returns 400"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_one_of_many(self, client, reset_activities):
        """Test unregistering one participant doesn't affect others"""
        # Verify initial state
        activities_response = client.get("/activities")
        initial_participants = activities_response.json()["Chess Club"]["participants"]
        assert len(initial_participants) == 2
        
        # Unregister one
        client.delete(
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu"
        )
        
        # Verify only one removed
        activities_response = client.get("/activities")
        remaining_participants = activities_response.json()["Chess Club"]["participants"]
        assert len(remaining_participants) == 1
        assert "daniel@mergington.edu" in remaining_participants


class TestSignupAndUnregisterFlow:
    """Tests for complete workflows"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up for an activity and then unregistering"""
        # Sign up
        signup_response = client.post(
            "/activities/Gym%20Class/signup?email=testuser@mergington.edu"
        )
        assert signup_response.status_code == 200
        
        # Verify signup worked
        activities_response = client.get("/activities")
        participants = activities_response.json()["Gym Class"]["participants"]
        assert "testuser@mergington.edu" in participants
        
        # Unregister
        unregister_response = client.delete(
            "/activities/Gym%20Class/unregister?email=testuser@mergington.edu"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregister worked
        activities_response = client.get("/activities")
        participants = activities_response.json()["Gym Class"]["participants"]
        assert "testuser@mergington.edu" not in participants
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test signing up for multiple activities"""
        student_email = "multiactivity@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            f"/activities/Chess%20Club/signup?email={student_email}"
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            f"/activities/Programming%20Class/signup?email={student_email}"
        )
        assert response2.status_code == 200
        
        # Verify both signups worked
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert student_email in activities_data["Chess Club"]["participants"]
        assert student_email in activities_data["Programming Class"]["participants"]
