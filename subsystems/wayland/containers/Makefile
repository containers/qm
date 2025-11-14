REGISTRY ?= quay.io/qm-images
PLATFORMS ?= linux/amd64,linux/arm64

TARGETS := wayland-compositor qm-dbus-broker

all: $(TARGETS)

.PHONY: $(TARGETS)
$(TARGETS):
	buildah build --platform $(PLATFORMS) --manifest $@ -f $@/Containerfile $@

.PHONY: push
push: all
	for name in $(TARGETS); do \
		buildah manifest push --all $$name docker://$(REGISTRY)/$$name || exit 1; \
	done

.PHONY: clean
clean:
	for name in $(TARGETS); do \
		buildah manifest rm $$name || true; \
	done