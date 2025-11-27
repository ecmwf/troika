#!/usr/bin/env python3

import os
import re
import logging
from troika.sites import Site
from troika import signals
from troika.config import Config

logger = logging.getLogger(__name__)

class LSFSite(Site):
    """LSF site handler for Troika"""

    # Commandes LSF
    SUBMIT_CMD = 'bsub'
    STATUS_CMD = 'bjobs'
    KILL_CMD = 'bkill'
    
    # États des jobs LSF
    STATE_MAP = {
        'PEND': 'pending',    # Pending
        'PSUSP': 'suspended', # Suspended (pending)
        'USUSP': 'suspended', # Suspended (user)
        'SSUSP': 'suspended', # Suspended (system)
        'RUN': 'running',     # Running
        'DONE': 'done',       # Completed successfully
        'EXIT': 'failed',     # Exited with error
        'UNKWN': 'unknown',   # Unknown
        'WAIT': 'pending',    # Waiting
    }

    def __init__(self, name, config):
        super().__init__(name, config)
        self.host = config.get('host', 'localhost')
        self.submit_cmd = config.get('submit_cmd', self.SUBMIT_CMD)
        self.status_cmd = config.get('status_cmd', self.STATUS_CMD)
        self.kill_cmd = config.get('kill_cmd', self.KILL_CMD)

    def submit(self, script_path, user, output, error, **kwargs):
        """Soumet un job LSF"""
        cmd = [self.submit_cmd]
        
        # Options de base
        cmd.extend(['-o', output])
        cmd.extend(['-e', error])
        
        # Resources LSF
        if 'queue' in kwargs:
            cmd.extend(['-q', kwargs['queue']])
        if 'job_name' in kwargs:
            cmd.extend(['-J', kwargs['job_name']])
        if 'walltime' in kwargs:
            # Conversion du format HH:MM:SS en minutes pour LSF
            time_parts = kwargs['walltime'].split(':')
            if len(time_parts) == 3:
                hours, minutes, _ = time_parts
                total_minutes = int(hours) * 60 + int(minutes)
                cmd.extend(['-W', str(total_minutes)])
        
        # Nombre de processeurs
        if 'np' in kwargs:
            cmd.extend(['-n', str(kwargs['np'])])
        elif 'nodes' in kwargs and 'ppn' in kwargs:
            total_procs = int(kwargs['nodes']) * int(kwargs['ppn'])
            cmd.extend(['-n', str(total_procs)])
            
        # Fichier de script
        cmd.append(script_path)
        
        # Exécution sur le host distant si nécessaire
        if self.host != 'localhost':
            full_cmd = ['ssh', self.host] + cmd
        else:
            full_cmd = cmd
            
        logger.debug("Submitting LSF job with command: %s", full_cmd)
        
        try:
            result = self._run_command(full_cmd)
            if result.returncode != 0:
                return None, f"Submission failed: {result.stderr}"
                
            # Extraction du job ID LSF
            match = re.search(r'Job <(\d+)>', result.stdout)
            if match:
                job_id = match.group(1)
                return job_id, None
            else:
                return None, "Could not parse job ID from output"
                
        except Exception as exc:
            return None, f"Submission error: {str(exc)}"

    def status(self, job_id, user):
        """Récupère le statut d'un job LSF"""
        cmd = [self.status_cmd, '-o', 'stat', '-noheader', job_id]
        
        if self.host != 'localhost':
            full_cmd = ['ssh', self.host] + cmd
        else:
            full_cmd = cmd
            
        try:
            result = self._run_command(full_cmd)
            if result.returncode != 0:
                if 'is not found' in result.stderr:
                    return 'done', None
                return None, f"Status check failed: {result.stderr}"
                
            # Nettoyage de la sortie
            lsf_state = result.stdout.strip()
            troika_state = self.STATE_MAP.get(lsf_state, 'unknown')
            return troika_state, None
                
        except Exception as exc:
            return None, f"Status error: {str(exc)}"

    def kill(self, job_id, user):
        """Tue un job LSF"""
        cmd = [self.kill_cmd, job_id]
        
        if self.host != 'localhost':
            full_cmd = ['ssh', self.host] + cmd
        else:
            full_cmd = cmd
            
        try:
            result = self._run_command(full_cmd)
            if result.returncode != 0:
                return f"Kill failed: {result.stderr}"
            return None
        except Exception as exc:
            return f"Kill error: {str(exc)}"

    def _run_command(self, cmd):
        """Exécute une commande et retourne le résultat"""
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return result


