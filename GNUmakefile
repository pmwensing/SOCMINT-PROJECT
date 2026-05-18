include Makefile

.PHONY: test-v11-final freeze-v11

test-v11-final: test-v11-9
	bash ./scripts/test_v11_final.sh

freeze-v11: test-v11-final
	@echo "v11 FINAL BASELINE frozen and ready for v12 handoff"
