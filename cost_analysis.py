from typing import List, Dict
from dataclasses import dataclass, field
from enum import Enum

print("="*60)
print("🔌 MULTI-PROVIDER CLIENT WITH FALLBACKS")
print("="*60)

class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    TOGETHER = "together"
    MOCK = "mock"

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: Provider
    context_window: int
    input_cost_per_1m: float  # $ per 1M tokens
    output_cost_per_1m: float
    is_reasoning: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = True
    max_output_tokens: int = 4096
    is_free: bool = False

# Comprehensive model configurations database
MODEL_CONFIGS = {
    # ============================================================
    # 🆓 FREE MODELS (Groq)
    # ============================================================
    "openai/gpt-oss-120b": ModelConfig(
        name="openai/gpt-oss-120b",
        provider=Provider.GROQ,
        context_window=128000,
        input_cost_per_1m=0.0,
        output_cost_per_1m=0.0,
        is_free=True
    ),
    "gemini-3-flash-preview": ModelConfig(
        name="gemini-3-flash-preview",
        provider=Provider.GOOGLE,
        context_window=1000000,
        input_cost_per_1m=0.5,
        output_cost_per_1m=3,
        supports_vision=True,
        is_free=True
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        provider=Provider.OPENAI,
        context_window=128000,
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        supports_vision=True
    )
}

print(f"\n📊 Loaded {len(MODEL_CONFIGS)} model configurations")





# ============================================================
# COMPREHENSIVE COST CALCULATOR
# ============================================================

print("="*60)
print("💰 COMPREHENSIVE COST CALCULATOR")
print("="*60)

class CostCalculator:
    """
    Calculate and project costs for LLM usage.
    Works with all models including free ones.
    """

    def __init__(self):
        self.model_configs = MODEL_CONFIGS

    def calculate_request_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict:
        """
        Calculate cost for a single request.
        """
        if model not in self.model_configs:
            # Return zero for unknown models
            return {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "input_cost": 0,
                "output_cost": 0,
                "total_cost": 0,
                "is_free": True
            }

        config = self.model_configs[model]

        input_cost = (input_tokens / 1_000_000) * config.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * config.output_cost_per_1m

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
            "is_free": config.is_free
        }

    def project_monthly_cost(
        self,
        model: str,
        avg_input_tokens: int,
        avg_output_tokens: int,
        requests_per_day: int
    ) -> Dict:
        """
        Project monthly costs based on usage patterns.
        """
        per_request = self.calculate_request_cost(model, avg_input_tokens, avg_output_tokens)

        daily_requests = requests_per_day
        monthly_requests = daily_requests * 30

        return {
            "model": model,
            "per_request_cost": per_request["total_cost"],
            "daily_cost": per_request["total_cost"] * daily_requests,
            "monthly_cost": per_request["total_cost"] * monthly_requests,
            "yearly_cost": per_request["total_cost"] * monthly_requests * 12,
            "monthly_requests": monthly_requests,
            "monthly_tokens": (avg_input_tokens + avg_output_tokens) * monthly_requests,
            "is_free": per_request["is_free"]
        }

    def compare_models_cost(
        self,
        avg_input_tokens: int,
        avg_output_tokens: int,
        requests_per_day: int,
        models: List[str] = None
    ) -> List[Dict]:
        """
        Compare costs across multiple models.
        """
        if models is None:
            models = list(self.model_configs.keys())

        projections = []
        for model in models:
            try:
                projection = self.project_monthly_cost(
                    model, avg_input_tokens, avg_output_tokens, requests_per_day
                )
                projections.append(projection)
            except:
                continue

        return sorted(projections, key=lambda x: x["monthly_cost"])

    def print_cost_comparison(
        self,
        avg_input_tokens: int,
        avg_output_tokens: int,
        requests_per_day: int
    ):
        """
        Print a formatted cost comparison table.
        """
        projections = self.compare_models_cost(
            avg_input_tokens, avg_output_tokens, requests_per_day
        )

        print(f"\n📊 Cost Projection for:")
        print(f"   • {avg_input_tokens} input tokens per request")
        print(f"   • {avg_output_tokens} output tokens per request")
        print(f"   • {requests_per_day:,} requests per day")

        print(f"\n{'Model':<40} {'Per Req':>12} {'Daily':>12} {'Monthly':>12}")
        print("─" * 80)

        for proj in projections:
            model_name = proj['model'][:38] + '..' if len(proj['model']) > 40 else proj['model']
            free_tag = "🆓" if proj['is_free'] else "  "

            if proj['monthly_cost'] == 0:
                print(f"{free_tag}{model_name:<37} {'FREE':>12} {'FREE':>12} {'FREE':>12}")
            else:
                print(f"{free_tag}{model_name:<37} ${proj['per_request_cost']:>10.6f} ${proj['daily_cost']:>10.2f} ${proj['monthly_cost']:>10.2f}")

        # Calculate savings
        paid_models = [p for p in projections if not p['is_free'] and p['monthly_cost'] > 0]
        if paid_models:
            cheapest_paid = paid_models[0]
            print(f"\n💡 Using FREE models saves ${cheapest_paid['monthly_cost']:,.2f}/month!")

# Create calculator and run examples
calculator = CostCalculator()

post_summary=425
starting_of_article=25
rest_of_chat=160



# Example 1: Customer Support Bot
print("\n" + "="*60)
print("social media post generator")
print("="*60)
calculator.print_cost_comparison(
    avg_input_tokens=(1070+445+530)/3,
    avg_output_tokens=(400+65+65)/3,
    requests_per_day=100
)