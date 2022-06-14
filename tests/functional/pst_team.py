import pytest
from pytest_bdd import given, scenario, then, when

class Team:
    knows_bdd: bool

    def __init__(self) -> None:
        self.knows_bdd = False

    def receive_bdd_demonstration(self) -> None:
        self.knows_bdd = True

    def can_define_behavioural_contracts(self) -> bool:
        return self.knows_bdd

    def can_auto_functional_testing(self) -> bool:
        return self.knows_bdd


@pytest.fixture()
def pst_team() -> Team:
    return Team()


@pytest.mark.skip
@scenario("features/pst_team.feature", "PST team learns BDD")
def test_pst_team_learns_bdd():
    pass


@given("the PST team does not know Gherkin")
def the_pst_team_does_not_know_gherkin(
    pst_team: Team,
):
    if pst_team.knows_bdd:
        pst_team.knows_bdd = False

    assert pst_team.can_define_behavioural_contracts() == False
    assert pst_team.can_auto_functional_testing() == False


@when("we are given a demonstration")
def we_are_given_a_demonstration(
    pst_team: Team,
):
    pst_team.receive_bdd_demonstration()


@then("we can use it to start defining behavioural contracts")
def we_can_use_it_to_start_defining_behavioural_contracts(
    pst_team: Team,
):
    assert pst_team.can_define_behavioural_contracts() == True


@then("we can then automate our functional testing")
def we_can_then_automate_our_functional_testing(
    pst_team: Team,
):
    assert pst_team.can_auto_functional_testing() == True
