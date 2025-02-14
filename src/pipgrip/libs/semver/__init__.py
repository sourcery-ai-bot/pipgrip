import re

from pipgrip.libs.semver.empty_constraint import EmptyConstraint  # noqa:F401
from pipgrip.libs.semver.patterns import (
    BASIC_CONSTRAINT,
    CARET_CONSTRAINT,
    TILDE_CONSTRAINT,
    TILDE_PEP440_CONSTRAINT,
    X_CONSTRAINT,
)
from pipgrip.libs.semver.version import Version
from pipgrip.libs.semver.version_constraint import VersionConstraint
from pipgrip.libs.semver.version_range import VersionRange
from pipgrip.libs.semver.version_union import VersionUnion

__version__ = "0.1.1"


def parse_constraint(constraints):  # type: (str) -> VersionConstraint
    if constraints == "*":
        return VersionRange()

    or_constraints = re.split(r"\s*\|\|?\s*", constraints.strip())
    or_groups = []
    for constraints in or_constraints:
        and_constraints = re.split(
            "(?<!^)(?<![=>< ,]) *(?<!-)[, ](?!-) *(?!,|$)", constraints
        )
        constraint_objects = []

        if len(and_constraints) > 1:
            for constraint in and_constraints:
                constraint_objects.append(parse_single_constraint(constraint))
        else:
            constraint_objects.append(parse_single_constraint(and_constraints[0]))

        constraint = constraint_objects[0]
        if len(constraint_objects) != 1:
            for next_constraint in constraint_objects[1:]:
                constraint = constraint.intersect(next_constraint)

        or_groups.append(constraint)

    return or_groups[0] if len(or_groups) == 1 else VersionUnion.of(*or_groups)


def parse_single_constraint(constraint):  # type: (str) -> VersionConstraint
    if m := re.match(r"(?i)^v?[xX*](\.[xX*])*$", constraint):
        return VersionRange()

    if m := TILDE_CONSTRAINT.match(constraint):
        version = Version.parse(m.group(1))

        high = version.stable.next_minor
        if len(m.group(1).split(".")) == 1:
            high = version.stable.next_major

        return VersionRange(
            version, high, include_min=True, always_include_max_prerelease=True
        )

    if m := TILDE_PEP440_CONSTRAINT.match(constraint):
        precision = 1
        if m.group(3):
            precision += 1

            if m.group(4):
                precision += 1

        version = Version.parse(m.group(1))

        low = version
        if precision == 2:
            high = version.stable.next_major
        else:
            high = version.stable.next_minor

        return VersionRange(
            low, high, include_min=True, always_include_max_prerelease=True
        )

    if m := CARET_CONSTRAINT.match(constraint):
        version = Version.parse(m.group(1))

        return VersionRange(
            version,
            version.next_breaking,
            include_min=True,
            always_include_max_prerelease=True,
        )

    if m := X_CONSTRAINT.match(constraint):
        op = m.group(1)
        major = int(m.group(2))
        minor = m.group(3)

        if minor is not None:
            version = Version(major, int(minor), 0)

            result = VersionRange(
                version,
                version.next_minor,
                include_min=True,
                always_include_max_prerelease=True,
            )
        elif major == 0:
            result = VersionRange(max=Version(1, 0, 0))
        else:
            version = Version(major, 0, 0)

            result = VersionRange(
                version,
                version.next_major,
                include_min=True,
                always_include_max_prerelease=True,
            )

        if op == "!=":
            result = VersionRange().difference(result)

        return result

    if m := BASIC_CONSTRAINT.match(constraint):
        op = m.group(1)
        version = m.group(2)

        if version == "dev":
            version = "0.0-dev"

        try:
            version = Version.parse(version)
        except ValueError:
            raise ValueError(f"Could not parse version constraint: {constraint}")

        if op == "<":
            return VersionRange(max=version)
        elif op == "<=":
            return VersionRange(max=version, include_max=True)
        elif op == ">":
            return VersionRange(min=version)
        elif op == ">=":
            return VersionRange(min=version, include_min=True)
        elif op == "!=":
            return VersionUnion(VersionRange(max=version), VersionRange(min=version))
        else:
            return version

    # VCS support
    try:
        return Version.parse(constraint)
    except ValueError:
        raise ValueError(f"Could not parse version constraint: {constraint}")

    raise ValueError(f"Could not parse version constraint: {constraint}")
