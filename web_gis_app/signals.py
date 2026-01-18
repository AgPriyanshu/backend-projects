from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import DatasetClosure, DatasetNode

# Cache to store old parent values before save
_old_parent_cache = {}


def create_ancestor_closures(node):
    """
    Create closure entries for a node based on its parent's ancestors.
    Returns the number of closures created.
    """
    if not node.parent:
        return 0

    parent_ancestors = DatasetClosure.objects.filter(descendant=node.parent)

    closures_to_create = [
        DatasetClosure(
            ancestor=closure.ancestor,
            descendant=node,
            depth=closure.depth + 1,
        )
        for closure in parent_ancestors
    ]

    DatasetClosure.objects.bulk_create(closures_to_create)

    return len(closures_to_create)


@receiver(pre_save, sender=DatasetNode)
def cache_old_parent(sender, instance, **kwargs):
    """
    Cache the old parent value before the instance is saved.
    This allows us to detect parent changes in post_save.
    """
    if instance.pk:  # Only for existing instances
        try:
            old_instance = DatasetNode.objects.get(pk=instance.pk)
            _old_parent_cache[instance.pk] = old_instance.parent_id
        except DatasetNode.DoesNotExist:
            _old_parent_cache[instance.pk] = None
    else:
        _old_parent_cache[instance.pk] = None


@receiver(post_save, sender=DatasetNode)
def maintain_transitive_closure(sender, instance, created, **kwargs):
    """
    Maintain transitive closure for hierarchical dataset nodes.

    When a node is created or its parent changes:
    1. Create self-reference (depth 0)
    2. Copy all ancestor relationships from parent
    3. Update depth for all descendants
    """
    if created:
        # Create self-reference closure (depth 0)
        DatasetClosure.objects.create(
            ancestor=instance,
            descendant=instance,
            depth=0,
        )

        # If this node has a parent, establish transitive closures
        create_ancestor_closures(instance)

        # Clean up cache
        _old_parent_cache.pop(instance.pk, None)
    else:
        # Handle parent change for existing nodes
        old_parent_id = _old_parent_cache.get(instance.pk)
        new_parent_id = instance.parent_id

        if old_parent_id != new_parent_id:
            # Parent has changed, rebuild closures

            # Delete all closures where this node is descendant (except self-reference)
            DatasetClosure.objects.filter(descendant=instance).exclude(
                ancestor=instance
            ).delete()

            # If new parent exists, create new closures
            create_ancestor_closures(instance)

            # Update closures for all descendants of this node
            rebuild_descendant_closures(instance)

        # Clean up cache
        _old_parent_cache.pop(instance.pk, None)


def rebuild_descendant_closures(node):
    """
    Rebuild closure relationships for all descendants of a node.
    This is needed when a node's parent changes.
    """
    # Get all direct children
    children = DatasetNode.objects.filter(parent=node)

    for child in children:
        # Delete old ancestor closures (except self-reference)
        DatasetClosure.objects.filter(descendant=child).exclude(ancestor=child).delete()

        # Create new closures based on current parent (node)
        create_ancestor_closures(child)

        # Recursively rebuild for this child's descendants
        rebuild_descendant_closures(child)
