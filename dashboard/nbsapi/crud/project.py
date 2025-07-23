import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from nbsapi.models import Project, NatureBasedSolution, Association
from nbsapi.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from nbsapi.crud.naturebasedsolution import build_nbs_schema_from_model


async def generate_project_id() -> str:
    """Generate a unique project ID"""
    return f"proj-{uuid.uuid4().hex[:8]}"


async def get_project(db_session: AsyncSession, project_id: str) -> ProjectRead:
    """
    Get a project by ID
    """
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Convert solutions to schemas
    areas = [
        await build_nbs_schema_from_model(solution) for solution in project.solutions
    ]

    # Convert to schema
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=project.map_settings,
        targets=project.targets,
        areas=areas,
    )


async def get_all_projects(db_session: AsyncSession) -> list[ProjectRead]:
    """
    Get all projects
    """
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
    )
    projects = result.scalars().unique()

    result = []
    for project in projects:
        # Convert solutions to schemas
        areas = [
            await build_nbs_schema_from_model(solution)
            for solution in project.solutions
        ]

        result.append(
            ProjectRead(
                id=project.id,
                title=project.title,
                description=project.description,
                settings=project.settings,
                map=project.map_settings,
                targets=project.targets,
                areas=areas,
            )
        )

    return result


async def create_project(
    db_session: AsyncSession,
    project_data: ProjectCreate,
    override_id: str | None = None,
) -> ProjectRead:
    """
    Create a new project
    """
    # Use override ID if provided, otherwise generate one
    if override_id:
        project_id = override_id
    else:
        project_id = await generate_project_id()

    # Check if project with this ID already exists
    existing = await db_session.get(Project, project_id)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Project with ID {project_id} already exists"
        )

    # Create the project
    project = Project(
        id=project_id,
        title=project_data.title,
        description=project_data.description,
        settings=project_data.settings.model_dump(exclude_none=True)
        if project_data.settings
        else None,
        map_settings=project_data.map.model_dump(exclude_none=True)
        if project_data.map
        else None,
        targets=project_data.targets.model_dump(exclude_none=True)
        if project_data.targets
        else None,
    )

    # Add NBS solutions if provided
    if project_data.areas:
        with db_session.no_autoflush:
            for nbs_id in project_data.areas:
                # Verify that the NBS exists
                nbs = await db_session.get(NatureBasedSolution, nbs_id)
                if not nbs:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Nature-based solution with ID {nbs_id} not found",
                    )
                project.solutions.append(nbs)

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Load solutions with relationships for schema conversion
    if project_data.areas:
        solutions_with_relationships = []
        for nbs_id in project_data.areas:
            nbs_result = await db_session.execute(
                select(NatureBasedSolution)
                .options(
                    joinedload(NatureBasedSolution.solution_targets).joinedload(
                        Association.tg
                    )
                )
                .where(NatureBasedSolution.id == nbs_id)
            )
            nbs = nbs_result.scalars().first()
            solutions_with_relationships.append(nbs)

        areas = [
            await build_nbs_schema_from_model(solution)
            for solution in solutions_with_relationships
        ]
    else:
        areas = []

    # Convert to schema and return
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=project.map_settings,
        targets=project.targets,
        areas=areas,
    )


async def update_project(
    db_session: AsyncSession, project_id: str, project_data: ProjectUpdate
) -> ProjectRead:
    """
    Update an existing project
    """
    # Get the project with relationships
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields if provided
    if project_data.title is not None:
        project.title = project_data.title

    if project_data.description is not None:
        project.description = project_data.description

    if project_data.settings is not None:
        project.settings = project_data.settings.model_dump(exclude_none=True)

    if project_data.map is not None:
        project.map_settings = project_data.map.model_dump(exclude_none=True)

    if project_data.targets is not None:
        project.targets = project_data.targets.model_dump(exclude_none=True)

    # Update NBS solutions if provided
    updated_solutions = None
    if project_data.areas is not None:
        with db_session.no_autoflush:
            # Clear existing solutions
            project.solutions = []
            updated_solutions = []

            # Add new solutions
            for nbs_id in project_data.areas:
                # Get the solution (no need for relationships here, just for validation)
                nbs = await db_session.get(NatureBasedSolution, nbs_id)
                if not nbs:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Nature-based solution with ID {nbs_id} not found",
                    )
                project.solutions.append(nbs)
                updated_solutions.append(nbs)

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Convert solutions to schemas using appropriate source
    if updated_solutions is not None:
        # Load the updated solutions with relationships for schema conversion
        solutions_with_relationships = []
        for solution in updated_solutions:
            nbs_result = await db_session.execute(
                select(NatureBasedSolution)
                .options(
                    joinedload(NatureBasedSolution.solution_targets).joinedload(
                        Association.tg
                    )
                )
                .where(NatureBasedSolution.id == solution.id)
            )
            nbs = nbs_result.scalars().first()
            solutions_with_relationships.append(nbs)

        areas = [
            await build_nbs_schema_from_model(solution)
            for solution in solutions_with_relationships
        ]
    else:
        # Use the existing solutions (they were eagerly loaded when fetching the project)
        areas = [
            await build_nbs_schema_from_model(solution)
            for solution in project.solutions
        ]

    # Convert to schema and return
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=project.map_settings,
        targets=project.targets,
        areas=areas,
    )


async def delete_project(db_session: AsyncSession, project_id: str) -> bool:
    """
    Delete a project
    """
    # Get the project
    project = await db_session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete the project
    await db_session.delete(project)
    await db_session.commit()

    return True


async def add_solution_to_project(
    db_session: AsyncSession, project_id: str, solution_id: int
) -> ProjectRead:
    """
    Add a nature-based solution to a project
    """
    # Get the project with relationships
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the solution with relationships
    solution_result = await db_session.execute(
        select(NatureBasedSolution)
        .options(
            joinedload(NatureBasedSolution.solution_targets).joinedload(Association.tg)
        )
        .options(joinedload(NatureBasedSolution.impacts))
        .where(NatureBasedSolution.id == solution_id)
    )
    solution = solution_result.scalars().first()
    if not solution:
        raise HTTPException(
            status_code=404,
            detail=f"Nature-based solution with ID {solution_id} not found",
        )

    # Check if the solution is already in the project
    if solution in project.solutions:
        raise HTTPException(
            status_code=409,
            detail=f"Solution {solution_id} is already in project {project_id}",
        )

    # Add the solution to the project
    project.solutions.append(solution)

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Re-fetch project with all relationships to avoid MissingGreenlet
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    refreshed_project = result.scalars().first()

    # Convert solutions to schemas
    areas = [
        await build_nbs_schema_from_model(solution)
        for solution in refreshed_project.solutions
    ]

    # Convert to schema and return
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=project.map_settings,
        targets=project.targets,
        areas=areas,
    )


async def remove_solution_from_project(
    db_session: AsyncSession, project_id: str, solution_id: int
) -> ProjectRead:
    """
    Remove a nature-based solution from a project
    """
    # Get the project with relationships
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the solution with relationships
    solution_result = await db_session.execute(
        select(NatureBasedSolution)
        .options(
            joinedload(NatureBasedSolution.solution_targets).joinedload(Association.tg)
        )
        .options(joinedload(NatureBasedSolution.impacts))
        .where(NatureBasedSolution.id == solution_id)
    )
    solution = solution_result.scalars().first()
    if not solution:
        raise HTTPException(
            status_code=404,
            detail=f"Nature-based solution with ID {solution_id} not found",
        )

    # Check if the solution is in the project
    if solution not in project.solutions:
        raise HTTPException(
            status_code=409,
            detail=f"Solution {solution_id} is not in project {project_id}",
        )

    # Remove the solution from the project
    project.solutions.remove(solution)

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Re-fetch project with all relationships to avoid MissingGreenlet
    result = await db_session.execute(
        select(Project)
        .options(
            joinedload(Project.solutions)
            .joinedload(NatureBasedSolution.solution_targets)
            .joinedload(Association.tg)
        )
        .options(joinedload(Project.solutions).joinedload(NatureBasedSolution.impacts))
        .where(Project.id == project_id)
    )
    refreshed_project = result.scalars().first()

    # Convert solutions to schemas
    areas = [
        await build_nbs_schema_from_model(solution)
        for solution in refreshed_project.solutions
    ]

    # Convert to schema and return
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        settings=project.settings,
        map=project.map_settings,
        targets=project.targets,
        areas=areas,
    )
