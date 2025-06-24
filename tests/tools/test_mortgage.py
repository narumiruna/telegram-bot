from mortgage import Loan


class TestComputeLoanDetails:
    def test_loan_calculation_basic(self):
        # Test the core mortgage calculation logic directly
        loan = Loan(principal=100000.0, interest=0.05, term=30)

        assert loan.principal == 100000.0
        assert float(loan.interest) == 0.05
        assert loan.term == 30
        assert loan.monthly_payment > 0
        assert loan.total_paid > loan.principal

    def test_loan_calculation_different_values(self):
        loan = Loan(principal=250000.0, interest=0.035, term=15)

        assert loan.principal == 250000.0
        assert abs(float(loan.interest) - 0.035) < 0.001
        assert loan.term == 15
        assert loan.monthly_payment > 0

    def test_loan_calculation_small_loan(self):
        loan = Loan(principal=5000.0, interest=0.08, term=5)

        assert loan.principal == 5000.0
        assert float(loan.interest) == 0.08
        assert loan.term == 5
        assert loan.monthly_payment > 0

    def test_loan_calculation_low_interest(self):
        # Use a very low but non-zero interest rate instead of zero
        loan = Loan(principal=100000.0, interest=0.001, term=30)

        assert loan.principal == 100000.0
        assert float(loan.interest) == 0.001
        assert loan.monthly_payment > 0
        # Low interest means total paid should be close to principal
        assert float(loan.total_paid) < float(loan.principal) * 1.1

    def test_loan_calculation_high_interest(self):
        loan = Loan(principal=100000.0, interest=0.15, term=30)

        assert loan.principal == 100000.0
        assert float(loan.interest) == 0.15
        assert loan.monthly_payment > 0
        # High interest means much more total paid than principal
        assert loan.total_paid > loan.principal * 2
