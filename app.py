import os

from flask import Flask, render_template, request

app = Flask(__name__)


def _get_int_env(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


@app.context_processor
def inject_ad_config():
    return {
        "coupang_partners_id": _get_int_env("COUPANG_PARTNERS_ID"),
        "coupang_tracking_code": os.getenv("COUPANG_TRACKING_CODE", "").strip() or None,
        "coupang_template": os.getenv("COUPANG_TEMPLATE", "carousel").strip() or "carousel",
        "coupang_width": _get_int_env("COUPANG_WIDTH") or 260,
        "coupang_height": _get_int_env("COUPANG_HEIGHT") or 300,
    }

@app.route('/health')
def health_check():
    return {"status": "ok"}, 200

@app.route('/')
def index():
    return render_template('index.html')

# Placeholder routes for other calculators
@app.route('/finance/dividend-calculator', methods=['GET', 'POST'])
def dividend_calculator():
    result = None
    if request.method == 'POST':
        try:
            investment_amount = float(request.form['investment_amount'].replace(',', ''))
            dividend_yield = float(request.form['dividend_yield']) / 100  # %를 소수로
            tax_rate = 0.154  # 2025년 배당소득세 15.4% (소득세 14% + 지방소득세 1.4%)
            
            # 연간 배당금 계산
            annual_dividend = investment_amount * dividend_yield
            
            # 세금 공제
            tax_amount = annual_dividend * tax_rate
            net_dividend = annual_dividend - tax_amount
            
            # 월 배당금 (연간 / 12)
            monthly_dividend = net_dividend / 12
            
            result = {
                'investment_amount': f"{int(round(investment_amount)):,}원",
                'dividend_yield': f"{request.form['dividend_yield']}%",
                'annual_dividend': f"{int(round(annual_dividend)):,}원",
                'tax_amount': f"{int(round(tax_amount)):,}원",
                'net_dividend': f"{int(round(net_dividend)):,}원",
                'monthly_dividend': f"{int(round(monthly_dividend)):,}원"
            }
        except ValueError:
            result = {'error': '입력값을 확인해주세요.'}
    
    return render_template('dividend_calculator.html', result=result)

@app.route('/finance/compound-interest-calculator', methods=['GET', 'POST'])
def compound_interest_calculator():
    result = None
    if request.method == 'POST':
        def _fmt_won(value: float) -> str:
            return f"{int(round(value)):,}원"

        try:
            mode = request.form.get('mode', 'basic')

            if mode == 'installment':
                start_amount = float(request.form['inst_start_amount'])
                monthly_contribution = float(request.form['inst_monthly_contribution'])
                period_value = int(request.form['inst_period_value'])
                period_unit = request.form.get('inst_period_unit', 'years')  # years|months
                rate_value = float(request.form['inst_rate_value'])
                rate_unit = request.form.get('inst_rate_unit', 'year')  # year|month
                compounding_method = request.form.get('inst_compounding_method', 'annual')  # annual|monthly

                if period_value <= 0:
                    raise ValueError('기간은 1 이상이어야 합니다.')
                if start_amount < 0 or monthly_contribution < 0:
                    raise ValueError('금액은 0 이상이어야 합니다.')
                if rate_value < 0:
                    raise ValueError('이자율은 0 이상이어야 합니다.')

                total_months = period_value * 12 if period_unit == 'years' else period_value
                if total_months <= 0:
                    raise ValueError('기간을 확인해주세요.')

                if rate_unit == 'year':
                    annual_rate = rate_value / 100.0
                    monthly_rate_input = None
                else:
                    annual_rate = None
                    monthly_rate_input = rate_value / 100.0

                rows = []

                if compounding_method == 'monthly':
                    if monthly_rate_input is not None:
                        monthly_rate = monthly_rate_input
                    else:
                        monthly_rate = (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0

                    balance = start_amount
                    total_contributed = start_amount
                    for month in range(1, total_months + 1):
                        if month >= 2:
                            balance += monthly_contribution
                            total_contributed += monthly_contribution
                        interest_gain = balance * monthly_rate
                        balance += interest_gain
                        return_rate = (balance / total_contributed - 1.0) * 100.0 if total_contributed > 0 else 0.0
                        rows.append({
                            'idx': month,
                            'profit': _fmt_won(interest_gain),
                            'total': _fmt_won(balance),
                            'return_rate': f"{return_rate:.2f}%"
                        })

                else:
                    if annual_rate is not None:
                        annual_rate_used = annual_rate
                    else:
                        annual_rate_used = (1.0 + monthly_rate_input) ** 12.0 - 1.0

                    balance = start_amount
                    total_contributed = start_amount
                    for month in range(1, total_months + 1):
                        if month >= 2:
                            balance += monthly_contribution
                            total_contributed += monthly_contribution
                        interest_gain = 0.0
                        if month % 12 == 0:
                            interest_gain = balance * annual_rate_used
                            balance += interest_gain
                        return_rate = (balance / total_contributed - 1.0) * 100.0 if total_contributed > 0 else 0.0
                        rows.append({
                            'idx': month,
                            'profit': _fmt_won(interest_gain),
                            'total': _fmt_won(balance),
                            'return_rate': f"{return_rate:.2f}%"
                        })

                total_contributed = start_amount + monthly_contribution * max(0, total_months - 1)
                total_profit = balance - total_contributed

                result = {
                    'mode': 'installment',
                    'total_profit': _fmt_won(total_profit),
                    'final_amount': _fmt_won(balance),
                    'rows': rows
                }

            else:
                principal = float(request.form['basic_principal'])
                periods = int(request.form['basic_period'])
                rate = float(request.form['basic_rate']) / 100.0

                if principal < 0:
                    raise ValueError('초기 금액은 0 이상이어야 합니다.')
                if periods <= 0:
                    raise ValueError('복리 횟수(기간)는 1 이상이어야 합니다.')
                if rate < 0:
                    raise ValueError('수익률은 0 이상이어야 합니다.')

                final_amount = principal * (1.0 + rate) ** periods
                total_profit = final_amount - principal

                rows = []
                balance = principal
                for i in range(1, periods + 1):
                    period_profit = balance * rate
                    balance += period_profit
                    cumulative_return = (balance / principal - 1.0) * 100.0 if principal > 0 else 0.0
                    rows.append({
                        'idx': i,
                        'profit': _fmt_won(period_profit),
                        'total': _fmt_won(balance),
                        'return_rate': f"{cumulative_return:.2f}%"
                    })

                result = {
                    'mode': 'basic',
                    'total_profit': _fmt_won(total_profit),
                    'final_amount': _fmt_won(final_amount),
                    'rows': rows
                }

        except (ValueError, KeyError):
            result = {'error': '입력값을 확인해주세요.'}
    
    return render_template('compound_interest_calculator.html', result=result)

@app.route('/finance/stock-return-calculator', methods=['GET', 'POST'])
def stock_return_calculator():
    result = None
    if request.method == 'POST':
        try:
            buy_price = float(request.form['buy_price'].replace(',', ''))
            sell_price = float(request.form['sell_price'].replace(',', ''))
            quantity = int(request.form['quantity'].replace(',', ''))
            fee_rate = float(request.form.get('fee_rate', 0.015)) / 100.0
            tax_rate = float(request.form.get('tax_rate', 0.23)) / 100.0

            if buy_price <= 0 or sell_price < 0 or quantity <= 0:
                raise ValueError('입력값을 확인해주세요.')

            total_buy = buy_price * quantity
            total_sell = sell_price * quantity
            buy_fee = total_buy * fee_rate
            sell_fee = total_sell * fee_rate
            tax_amount = total_sell * tax_rate
            profit_loss = total_sell - total_buy - buy_fee - sell_fee - tax_amount
            cost_basis = total_buy + buy_fee
            return_rate = (profit_loss / cost_basis * 100.0) if cost_basis > 0 else 0.0

            result = {
                'buy_price': f"{int(round(buy_price)):,}",
                'sell_price': f"{int(round(sell_price)):,}",
                'quantity': f"{quantity:,}",
                'total_buy': f"{int(round(total_buy)):,}",
                'total_sell': f"{int(round(total_sell)):,}",
                'fee_total': f"{int(round(buy_fee + sell_fee)):,}",
                'tax_amount': f"{int(round(tax_amount)):,}",
                'profit_loss': f"{int(round(profit_loss)):,}",
                'return_rate': f"{return_rate:.2f}"
            }
        except ValueError:
            result = {'error': '입력값을 확인해주세요.'}
    
    return render_template('stock_return_calculator.html', result=result)

@app.route('/finance/average-price-calculator')
def average_price_calculator():
    return render_template('average_price_calculator.html')

@app.route('/loan/loan-interest-calculator', methods=['GET', 'POST'])
def loan_interest_calculator():
    result = None
    if request.method == 'POST':
        try:
            loan_amount = float(request.form['loan_amount'])
            interest_rate = float(request.form['interest_rate']) / 100
            loan_term_years = int(request.form['loan_term'])
            repayment_type = request.form['repayment_type']
            
            monthly_rate = interest_rate / 12
            total_months = loan_term_years * 12
            
            if repayment_type == 'equal_principal_interest':
                # 원리금 균등 상환
                if monthly_rate == 0:
                    monthly_payment = loan_amount / total_months
                else:
                    monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**total_months) / ((1 + monthly_rate)**total_months - 1)
                total_payment = monthly_payment * total_months
                total_interest = total_payment - loan_amount
            else:
                # 원금 균등 상환 (간단 계산)
                principal_payment = loan_amount / total_months
                total_interest = 0
                remaining_balance = loan_amount
                for month in range(1, total_months + 1):
                    interest_payment = remaining_balance * monthly_rate
                    total_interest += interest_payment
                    remaining_balance -= principal_payment
                # 평균 월 상환액 (실제로는 변동)
                monthly_payment = principal_payment + (total_interest / total_months)
                total_payment = loan_amount + total_interest
            
            result = {
                'monthly_payment': f"{round(monthly_payment):,}",
                'total_payment': f"{round(total_payment):,}",
                'total_interest': f"{round(total_interest):,}",
                'interest_rate': request.form['interest_rate']
            }
        except ValueError:
            result = {'error': '입력값을 확인해주세요.'}
    
    return render_template('loan_interest_calculator.html', result=result)

@app.route('/loan/equal-principal-interest-calculator')
def equal_principal_interest_calculator():
    return render_template('equal_principal_interest_calculator.html')

@app.route('/loan/equal-principal-calculator')
def equal_principal_calculator():
    return render_template('equal_principal_calculator.html')

@app.route('/real-estate/rent-to-monthly-calculator')
def rent_to_monthly_calculator():
    return render_template('rent_to_monthly_calculator.html')

@app.route('/real-estate/acquisition-tax-calculator')
def acquisition_tax_calculator():
    return render_template('acquisition_tax_calculator.html')

@app.route('/real-estate/brokerage-fee-calculator')
def brokerage_fee_calculator():
    return render_template('brokerage_fee_calculator.html')

@app.route('/salary/net-salary-calculator', methods=['GET', 'POST'])
def net_salary_calculator():
    result = None
    if request.method == 'POST':
        try:
            annual_salary = float(request.form['annual_salary'].replace(',', '')) * 10000  # 기본 연봉 (만원 단위 입력)
            dependents = int(request.form['dependents'].replace(',', ''))
            non_taxable_monthly = float(request.form.get('non_taxable', '20').replace(',', '')) * 10000  # 기타 비과세 (월)
            meal_allowance_monthly = float(request.form.get('meal_allowance', '20').replace(',', '')) * 10000  # 식대 (월)
            night_allowance_monthly = float(request.form.get('night_allowance', '0').replace(',', '')) * 10000  # 야간/교통 등 과세 수당 (월)
            bonus_annual = float(request.form.get('bonus_annual', '0').replace(',', '')) * 10000  # 보너스 (연, 만원)
            pension_contrib_monthly = float(request.form.get('pension_contrib', '0').replace(',', '')) * 10000  # 퇴직연금 본인부담 (월)

            # 식대 비과세 한도 (월 200,000원)
            meal_tax_free_cap = 200000
            meal_tax_free_monthly = min(meal_allowance_monthly, meal_tax_free_cap)
            meal_taxable_monthly = max(meal_allowance_monthly - meal_tax_free_cap, 0)

            # 연 단위 환산
            night_allowance_annual = night_allowance_monthly * 12
            meal_annual = meal_allowance_monthly * 12
            meal_tax_free_annual = meal_tax_free_monthly * 12
            meal_taxable_annual = meal_taxable_monthly * 12
            other_non_tax_annual = non_taxable_monthly * 12
            pension_contrib_annual = pension_contrib_monthly * 12

            # 과세 대상 급여 (연) = 기본연봉 + 보너스 + 과세 수당 + 식대 과세분
            taxable_cash_annual = annual_salary + bonus_annual + night_allowance_annual + meal_taxable_annual
            # 총 현금 수령 (연) = 과세 대상 급여 + 비과세(식대 비과세 + 기타 비과세)
            gross_cash_annual = taxable_cash_annual + meal_tax_free_annual + other_non_tax_annual

            monthly_taxable_for_insurance = taxable_cash_annual / 12

            # 국민연금 (4.5%, 상한 5,530,000원, 2025년 기준)
            national_pension_monthly = min(monthly_taxable_for_insurance * 0.045, 5530000)
            national_pension = national_pension_monthly * 12
            
            # 건강보험 (3.545%)
            health_insurance_monthly = monthly_taxable_for_insurance * 0.03545
            health_insurance = health_insurance_monthly * 12
            
            # 장기요양보험 (건강보험의 12.81%)
            long_term_care_monthly = health_insurance_monthly * 0.1281
            long_term_care = long_term_care_monthly * 12
            
            # 고용보험 (0.9%)
            employment_insurance_monthly = monthly_taxable_for_insurance * 0.009
            employment_insurance = employment_insurance_monthly * 12
            
            # 과세소득 산출: 과세급여 - 4대보험 - 기본공제 - 비과세 - 퇴직연금 본인부담
            taxable_income = taxable_cash_annual - (national_pension + health_insurance + long_term_care + employment_insurance) - (dependents * 1500000) - other_non_tax_annual - meal_tax_free_annual - pension_contrib_annual
            
            if taxable_income <= 0:
                income_tax = 0
            else:
                # 2025년 누진세율
                if taxable_income <= 12000000:
                    income_tax = taxable_income * 0.06
                elif taxable_income <= 46000000:
                    income_tax = 12000000 * 0.06 + (taxable_income - 12000000) * 0.15
                elif taxable_income <= 88000000:
                    income_tax = 12000000 * 0.06 + 34000000 * 0.15 + (taxable_income - 46000000) * 0.24
                elif taxable_income <= 150000000:
                    income_tax = 12000000 * 0.06 + 34000000 * 0.15 + 42000000 * 0.24 + (taxable_income - 88000000) * 0.35
                else:
                    income_tax = 12000000 * 0.06 + 34000000 * 0.15 + 42000000 * 0.24 + 62000000 * 0.35 + (taxable_income - 150000000) * 0.38
            
            local_income_tax = income_tax * 0.1
            total_deductions = national_pension + health_insurance + long_term_care + employment_insurance + income_tax + local_income_tax + pension_contrib_annual
            net_salary = gross_cash_annual - total_deductions
            monthly_net = net_salary / 12
            
            result = {
                'annual_salary': f"{round(annual_salary / 10000):,}만원",
                'bonus_annual': f"{round(bonus_annual / 10000):,}만원",
                'night_allowance': f"{round(night_allowance_annual):,}",
                'meal_tax_free': f"{round(meal_tax_free_annual):,}",
                'meal_taxable': f"{round(meal_taxable_annual):,}",
                'other_non_tax': f"{round(other_non_tax_annual):,}",
                'pension_contrib': f"{round(pension_contrib_annual):,}",
                'taxable_cash': f"{round(taxable_cash_annual):,}",
                'gross_cash': f"{round(gross_cash_annual):,}",
                'national_pension': f"{round(national_pension):,}",
                'health_insurance': f"{round(health_insurance):,}",
                'long_term_care': f"{round(long_term_care):,}",
                'employment_insurance': f"{round(employment_insurance):,}",
                'income_tax': f"{round(income_tax):,}",
                'local_income_tax': f"{round(local_income_tax):,}",
                'total_deductions': f"{round(total_deductions):,}",
                'net_salary': f"{round(net_salary):,}",
                'monthly_net': f"{round(monthly_net):,}"
            }
        except ValueError:
            result = {'error': '입력값을 확인해주세요.'}
    
    return render_template('net_salary_calculator.html', result=result)

@app.route('/salary/retirement-pay-calculator')
def retirement_pay_calculator():
    return render_template('retirement_pay_calculator.html')

@app.route('/salary/vat-calculator')
def vat_calculator():
    return render_template('vat_calculator.html')

@app.route('/life/bmi-calculator')
def bmi_calculator():
    return render_template('bmi_calculator.html')

@app.route('/life/age-calculator')
def age_calculator():
    return render_template('age_calculator.html')

@app.route('/life/d-day-calculator')
def d_day_calculator():
    return render_template('d_day_calculator.html')

# Category routes
@app.route('/finance')
def finance():
    return render_template('category.html', category_name='금융 · 투자')

@app.route('/loan')
def loan():
    return render_template('category.html', category_name='대출 · 이자')

@app.route('/real-estate')
def real_estate():
    return render_template('category.html', category_name='부동산')

@app.route('/salary')
def salary():
    return render_template('category.html', category_name='직장인 · 세금')

@app.route('/life')
def life():
    return render_template('category.html', category_name='생활')

@app.route('/basic')
def basic():
    return render_template('category.html', category_name='기본 계산기')

# Add more routes as needed...

if __name__ == '__main__':
    app.run(debug=True)
