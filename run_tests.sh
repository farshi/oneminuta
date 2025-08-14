#!/bin/bash
# OneMinuta Test Runner
# Quick access to test suite from project root

echo "🧪 OneMinuta Test Suite"
echo "======================="
echo ""
echo "Available test commands:"
echo ""
echo "Quick tests (no API required):"
echo "  ./run_tests.sh quick"
echo ""
echo "All chatbot tests:"
echo "  ./run_tests.sh chatbot"
echo ""
echo "Integration tests:"
echo "  ./run_tests.sh integration"
echo ""
echo "All tests:"
echo "  ./run_tests.sh all"
echo ""
echo "Telegram bot test:"
echo "  ./run_tests.sh telegram"
echo ""

case "$1" in
  quick)
    python tests/run_all_tests.py --category quick
    ;;
  chatbot)
    python tests/run_all_tests.py --category chatbot
    ;;
  integration)
    python tests/run_all_tests.py --category integration
    ;;
  all)
    python tests/run_all_tests.py --category all
    ;;
  telegram)
    python tests/integration/start_telegram_chatbot_test.py
    ;;
  *)
    echo "Usage: ./run_tests.sh [quick|chatbot|integration|all|telegram]"
    echo ""
    echo "Running quick tests by default..."
    python tests/run_all_tests.py --category quick
    ;;
esac