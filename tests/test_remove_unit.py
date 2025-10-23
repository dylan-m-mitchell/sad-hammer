"""Tests for removing AI units (when killed by player)."""

import pytest
from full_simulator import SoloSimulator, Unit


class TestSimulatorRemoveUnit:
    """Test the remove_unit method in SoloSimulator."""
    
    def test_remove_existing_unit(self):
        """Should successfully remove a unit that exists."""
        units = [
            Unit('Unit A', aggression='Aggressive'),
            Unit('Unit B', aggression='Neutral'),
            Unit('Unit C', aggression='Cautious'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        assert len(sim.units) == 3
        
        # Remove Unit B
        result = sim.remove_unit('Unit B')
        
        assert result is True
        assert len(sim.units) == 2
        assert 'Unit B' not in [u.name for u in sim.units]
        assert 'Unit A' in [u.name for u in sim.units]
        assert 'Unit C' in [u.name for u in sim.units]
    
    def test_remove_nonexistent_unit(self):
        """Should return False when trying to remove a unit that doesn't exist."""
        units = [
            Unit('Unit A', aggression='Aggressive'),
            Unit('Unit B', aggression='Neutral'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        assert len(sim.units) == 2
        
        # Try to remove a unit that doesn't exist
        result = sim.remove_unit('Unit Z')
        
        assert result is False
        assert len(sim.units) == 2  # No units removed
    
    def test_remove_all_units(self):
        """Should be able to remove all units sequentially."""
        units = [
            Unit('Unit A', aggression='Aggressive'),
            Unit('Unit B', aggression='Neutral'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        assert len(sim.units) == 2
        
        # Remove both units
        assert sim.remove_unit('Unit A') is True
        assert len(sim.units) == 1
        
        assert sim.remove_unit('Unit B') is True
        assert len(sim.units) == 0
    
    def test_remove_first_unit(self):
        """Should correctly remove the first unit in the list."""
        units = [
            Unit('First', aggression='Aggressive'),
            Unit('Second', aggression='Neutral'),
            Unit('Third', aggression='Cautious'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        result = sim.remove_unit('First')
        
        assert result is True
        assert len(sim.units) == 2
        assert sim.units[0].name == 'Second'
        assert sim.units[1].name == 'Third'
    
    def test_remove_last_unit(self):
        """Should correctly remove the last unit in the list."""
        units = [
            Unit('First', aggression='Aggressive'),
            Unit('Second', aggression='Neutral'),
            Unit('Last', aggression='Cautious'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        result = sim.remove_unit('Last')
        
        assert result is True
        assert len(sim.units) == 2
        assert sim.units[0].name == 'First'
        assert sim.units[1].name == 'Second'
    
    def test_simulator_continues_after_unit_removal(self):
        """Simulator should continue to work normally after removing a unit."""
        units = [
            Unit('Unit A', aggression='Aggressive'),
            Unit('Unit B', aggression='Neutral'),
            Unit('Unit C', aggression='Cautious'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        # Run a turn
        events1 = sim.simulate_turn()
        assert len(events1) > 0
        
        # Remove a unit
        sim.remove_unit('Unit B')
        assert len(sim.units) == 2
        
        # Run another turn - should work fine with 2 units
        events2 = sim.simulate_turn()
        assert len(events2) > 0
        
        # Check that Unit B is not in any events
        for event in events2:
            if 'unit' in event:
                assert event['unit'] != 'Unit B'
    
    def test_remove_unit_case_sensitive(self):
        """Unit removal should be case-sensitive."""
        units = [
            Unit('Unit A', aggression='Aggressive'),
            Unit('Unit B', aggression='Neutral'),
        ]
        sim = SoloSimulator(units, seed=42)
        
        # Try to remove with wrong case
        result = sim.remove_unit('unit a')
        
        assert result is False
        assert len(sim.units) == 2  # No units removed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
