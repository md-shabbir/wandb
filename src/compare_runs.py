import os
import wandb
from wandb.apis import reports as wb_reports

# Validate API key presence before proceeding
api_key = os.getenv('WANDB_API_KEY')
if not api_key:
    raise ValueError('WANDB_API_KEY environment variable must be configured')

def retrieve_reference_run(entity_name='sbr543-oc', project_name='project-1', run_tag='baseline'):
    """
    Retrieves a reference run from the specified project using tag filtering.
    
    Args:
        entity_name: W&B entity/organization name
        project_name: Project name within the entity
        run_tag: Tag used to identify the baseline run
        
    Returns:
        The baseline run object
        
    Raises:
        AssertionError if exactly one run with the tag is not found
    """
    wandb_client = wandb.Api()
    filtered_runs = wandb_client.runs(
        f'{entity_name}/{project_name}', 
        {"tags": {"$in": [run_tag]}}
    )
    
    if len(filtered_runs) != 1:
        raise AssertionError(f'Expected exactly one run tagged "{run_tag}", found {len(filtered_runs)}')
    
    return filtered_runs[0]


def generate_comparison_report(entity_name='sbr543-oc',
                               project_name='project-1',
                               run_tag='baseline',
                               target_run_id=None):
    """
    Generates a comparison report between a target run and the baseline run.
    
    Environment variables can override default parameters:
    - WANDB_ENTITY: entity name
    - WANDB_PROJECT: project name  
    - BASELINE_TAG: baseline tag identifier
    - RUN_ID: target run identifier (required)
    
    Returns:
        URL of the generated report
    """
    # Read configuration from environment with fallback to defaults
    config = {
        'entity': os.getenv('WANDB_ENTITY', entity_name),
        'project': os.getenv('WANDB_PROJECT', project_name),
        'tag': os.getenv('BASELINE_TAG', run_tag),
        'run_id': os.getenv('RUN_ID') or target_run_id
    }
    
    if not config['run_id']:
        raise ValueError('RUN_ID must be provided via environment variable or function argument')

    # Obtain the baseline run for comparison
    baseline_run = retrieve_reference_run(
        entity_name=config['entity'],
        project_name=config['project'],
        run_tag=config['tag']
    )
    
    # Initialize report with metadata
    comparison_report = wb_reports.Report(
        entity=config['entity'],
        project=config['project'],
        title='Run Comparison Analysis',
        description=f'Comparison report: baseline is {baseline_run.name}'
    )
    
    # Configure run filter and comparison panel
    run_filter_expression = f"ID in ['{config['run_id']}', '{baseline_run.id}']"
    comparison_runset = wb_reports.Runset(
        config['entity'],
        config['project'],
        "Comparison Set"
    ).set_filters_with_python_expr(run_filter_expression)
    
    comparison_panel = wb_reports.RunComparer(
        diff_only='split',
        layout={'w': 24, 'h': 15}
    )
    
    comparison_grid = wb_reports.PanelGrid(
        runsets=[comparison_runset],
        panels=[comparison_panel]
    )
    
    # Insert comparison grid after first block
    original_blocks = comparison_report.blocks
    comparison_report.blocks = original_blocks[:1] + [comparison_grid] + original_blocks[1:]
    
    # Persist report to W&B
    comparison_report.save()
    
    # Export report URL for CI/CD integration
    is_ci_environment = os.getenv('CI') == 'true'
    if is_ci_environment and 'GITHUB_OUTPUT' in os.environ:
        github_output_path = os.environ['GITHUB_OUTPUT']
        with open(github_output_path, 'a') as output_file:
            output_file.write(f'REPORT_URL={comparison_report.url}\n')
    
    return comparison_report.url


if __name__ == '__main__':
    report_url = generate_comparison_report()
    print(f'Comparison report available at: {report_url}')
