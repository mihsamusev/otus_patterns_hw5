import math
import unittest
from unittest.mock import Mock

from src.command import (
    BurnFuelCommand,
    CanMoveWithFuel,
    CanRedirectVelocity,
    CanTurn,
    CanTurnWithVelocity,
    CheckFuelCommand,
    Command,
    CommandException,
    MacroCommand,
    MoveCommand,
    RedirectVelocityCommand,
    TurnCommand,
    UsesFuel,
)
from src.core import Vector2D

EPS_PLACES = 8


class TestMoveWithFuelFeature(unittest.TestCase):
    def test_check_fuel_allowed_burning_dont_raise_excepiton(self):
        body_with_fuel = Mock(spec_set=UsesFuel)
        body_with_fuel.fuel = 6
        body_with_fuel.burn_rate = 5
        CheckFuelCommand(body_with_fuel).execute()

        body_with_fuel.fuel = 5
        body_with_fuel.burn_rate = 5
        CheckFuelCommand(body_with_fuel).execute()

    def test_check_fuel_disallowed_burning_raise_excepiton(self):
        body_with_fuel = Mock(spec_set=UsesFuel)
        body_with_fuel.fuel = 4
        body_with_fuel.burn_rate = 5
        cmd = CheckFuelCommand(body_with_fuel)
        self.assertRaises(CommandException, cmd.execute)

    def test_burn_fuel_subtracts_fuel_by_burn_rate(self):
        body_with_fuel = Mock(spec_set=UsesFuel)
        body_with_fuel.fuel = 20
        body_with_fuel.burn_rate = 15
        BurnFuelCommand(body_with_fuel).execute()
        self.assertEqual(body_with_fuel.fuel, 5)


class TestMacroCommand(unittest.TestCase):
    def test_macro_executes_all_subcommands(self):
        body = Mock(spec_set=Command)
        commands = (body, body, body)
        MacroCommand(commands).execute()
        self.assertEqual(body.execute.call_count, 3)

    def test_macro_subcommand_execution_stops_on_2_out_of_3_due_to_exception(self):
        body = Mock(spec_set=Command)
        body.execute.side_effect = ("Ok", Exception(), "Ok")
        commands = (body, body, body)

        cmd = MacroCommand(commands)
        self.assertRaises(CommandException, cmd.execute)
        self.assertEqual(body.execute.call_count, 2)

    def test_concrete_macro_command_check_move_burn_executes_if_enough_fuel(self):
        movable_with_fuel = Mock(spec_set=CanMoveWithFuel)
        movable_with_fuel.position = Vector2D(x=1.0, y=2.0)
        movable_with_fuel.velocity = Vector2D(x=1.0, y=-1.0)
        movable_with_fuel.fuel = 15
        movable_with_fuel.burn_rate = 5

        cmd = MacroCommand(
            [
                CheckFuelCommand(movable_with_fuel),
                MoveCommand(movable_with_fuel),
                BurnFuelCommand(movable_with_fuel),
            ]
        )
        cmd.execute()
        expected_position = Vector2D(x=2.0, y=1.0)
        self.assertAlmostEqual(
            movable_with_fuel.position.x, expected_position.x, places=EPS_PLACES
        )
        self.assertAlmostEqual(
            movable_with_fuel.position.y, expected_position.y, places=EPS_PLACES
        )
        self.assertEqual(movable_with_fuel.fuel, 10)

    def test_concrete_macro_command_check_move_burn_raises_if_not_enough_fuel(self):
        movable_with_fuel = Mock(spec_set=CanMoveWithFuel)
        movable_with_fuel.position = Vector2D(x=1.0, y=2.0)
        movable_with_fuel.velocity = Vector2D(x=1.0, y=-1.0)
        movable_with_fuel.fuel = 1
        movable_with_fuel.burn_rate = 5

        cmd = MacroCommand(
            [
                CheckFuelCommand(movable_with_fuel),
                MoveCommand(movable_with_fuel),
                BurnFuelCommand(movable_with_fuel),
            ]
        )
        self.assertRaises(CommandException, cmd.execute)


class TestTurnFeature(unittest.TestCase):
    def test_turn_start_at_zero_turn_half_circle_get_to_half_circle(self):
        body = Mock(spec_set=CanTurn)
        body.direction = 0
        body.angular_velocity = 5
        body.max_directions = 10

        TurnCommand(body).execute()
        self.assertEqual(body.direction, 5)

    def test_turn_start_at_zero_turn_by_3_half_circles_get_to_half_circle(self):
        body = Mock(spec_set=CanTurn)
        body.direction = 0
        body.angular_velocity = 15
        body.max_directions = 10

        TurnCommand(body).execute()
        self.assertEqual(body.direction, 5)

    def test_turn_start_at_nonzero_turn_full_circle_get_back_to_start(self):
        body = Mock(spec_set=CanTurn)
        body.direction = 2
        body.angular_velocity = 10
        body.max_directions = 10

        TurnCommand(body).execute()
        self.assertEqual(body.direction, 2)

    def test_body_with_velocity_direction_doesnt_redirect_0_magnitude_velocity(self):
        body = Mock(spec_set=CanRedirectVelocity)
        body.direction = 5
        body.max_directions = 10
        body.velocity = Vector2D(x=0.0, y=0.0)

        RedirectVelocityCommand(body).execute()
        expected_velocity = Vector2D(x=0.0, y=0.0)
        self.assertAlmostEqual(body.velocity.x, expected_velocity.x, places=EPS_PLACES)
        self.assertAlmostEqual(body.velocity.y, expected_velocity.y, places=EPS_PLACES)

    def test_body_with_velocity_direction_redirects_velocity_and_keeps_magnitude(self):
        body = Mock(spec_set=CanRedirectVelocity)
        body.direction = 5
        body.max_directions = 10
        body.velocity = Vector2D(x=3.0, y=-4.0)

        RedirectVelocityCommand(body).execute()
        expected_velocity = Vector2D(x=-5.0, y=0.0)
        self.assertAlmostEqual(
            body.velocity.mag(), expected_velocity.mag(), places=EPS_PLACES
        )
        self.assertAlmostEqual(body.velocity.x, expected_velocity.x, places=EPS_PLACES)
        self.assertAlmostEqual(body.velocity.y, expected_velocity.y, places=EPS_PLACES)

    def test_two_step_turning_to_45deg_wraps_circle_and_updates_velocity(self):
        body = Mock(spec_set=CanTurnWithVelocity)
        body.direction = 22
        body.max_directions = 24
        body.angular_velocity = 5
        body.velocity = Vector2D(x=0.0, y=-5.0)

        commands = (TurnCommand(body), RedirectVelocityCommand(body))
        MacroCommand(commands).execute()

        vx45 = 5 * 0.5 * math.sqrt(2)
        expected_velocity = Vector2D(x=vx45, y=vx45)
        self.assertEqual(body.direction, 3)
        self.assertAlmostEqual(
            body.velocity.mag(), expected_velocity.mag(), places=EPS_PLACES
        )
        self.assertAlmostEqual(body.velocity.x, expected_velocity.x, places=EPS_PLACES)
        self.assertAlmostEqual(body.velocity.y, expected_velocity.y, places=EPS_PLACES)
