import logging
from agents import function_tool
from mortgage import Loan

logger = logging.getLogger(__name__)


@function_tool
def compute_loan_details(principal: float, interest: float, term: int) -> str:
    """Calculates and summarizes loan details based on provided parameters.

    Attributes:
        principal (float): The amount of money borrowed.
        interest (float): The annual interest rate as a decimal between 0 and 1.
        term (int): The loan duration in years.

    Note:
        - `term_unit` is assumed to be 'years'.
        - `compounded` is assumed to be 'monthly'.
        - `currency` is assumed to be '$'.

    Returns:
        str: A formatted summary of the loan details.
    """
    loan = Loan(
        principal=principal,
        interest=interest,
        term=term,
    )

    lines = [
        f"Original Balance: {loan._currency}{loan.principal:.2f}",
        f"Interest Rate: {loan.interest:.2f} %",
        f"APY: {loan.apy:.2f} %",
        f"APR: {loan.apr:.2f} %",
        f"Term: {loan.term:.2f} {loan.term_unit}",
        f"Monthly Payment: {loan._currency}{loan.monthly_payment:.2f}",
        f"Compound Frequency: {loan.compounded}",
        "",
        f"Total principal payments: {loan._currency}{loan.total_principal:.2f}",
        f"Total interest payments: {loan._currency}{loan.total_interest:.2f}",
        f"Total payments: {loan._currency}{loan.total_paid:.2f}",
        f"Interest to principal: {loan.interest_to_principle:.2f} %",
        f"Years to pay: {loan.years_to_pay:.2f}",
    ]

    res = "\n".join(lines)

    logger.info("Loan summary: {text}", text=res)
    return res
