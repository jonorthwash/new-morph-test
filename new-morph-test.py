"""

**to dos:
  -error checking
  -commenting
  -implementing the arg options 
  -print nicely
This script performs a morphological test on a file.
"""
from argparse import ArgumentParser
from collections import OrderedDict
from io import StringIO
import libhfst
import sys
import yaml
import time 

def error_checking(n):
    msg = 'Error: '
    if n == 2:   msg += '.'
    elif n == 3: msg += '.'
    elif n == 4: msg += '.'
    elif n == 5: msg += '.'
    elif n == 6: msg += '.'
    print(msg)
    sys.exit(num)

def argument_parsing():
    ap = ArgumentParser()
    ap.description = 'This script performs a morphological test.'

    h = 'Output style: compact, terse, final, normal (Default: normal)'
    ap.add_argument('-o', '--output', dest='output', default='normal', help=h)
    
    h = 'No output, only exit code.'
    ap.add_argument('-q', '--silent', dest='silent', action='store_true', help=h)

    h = 'Ignore unexpected analyses. Will pass if expected one is found.'
    ap.add_argument('-i', '--ignore-unexpected', dest='ignore', action='store_true', help=h)
    
    h = 'Surface input/analysis tests only'
    ap.add_argument('-s', '--surface', dest='surface', action='store_true', help=h)

    h = 'Lexical input/generation tests only'
    ap.add_argument('-l', '--lexical', dest='lexical', action='store_true', help=h)

    # remember this change
    h = 'Suppresses fails to make finding passes easier'
    ap.add_argument('-p', '--hide-fails', dest='hide_fail', action='store_true', help=h)

    # same change 
    h = 'Suppresses passes to make finding failures easier'
    ap.add_argument('-f', '--hide-passes', dest='hide_pass', action='store_true', help=h)

    # make this into choose what section to run
    h = 'The section to be used for testing (default is `hfst`)'
    ap.add_argument('-S', '--section', default='hfst', dest='section', 
                    nargs='?', required=False, help=h)
    
    # make required and this says what language code
    h = 'Which fallback transducer to use.'
    ap.add_argument('-F', '--fallback', dest='transducer', nargs='?', required=False, help=h)
    h = 'More verbose output.' 
    ap.add_argument('-v', '--verbose', dest='verbose', action='store_true', help=h)
    # add 'do not analyse' negation (for spellchecker testing)
    # add verbose
    
    ap.add_argument('file', help='YAML file with test rules')

    arguments = ap.parse_args()
    return arguments

def define_colors():
    colors = {}
    colors['red'] = '\033[0;31m'
    colors['green'] = '\033[0;32m'
    colors['orange'] = '\033[0;33m'
    colors['yellow'] = '\033[1;33m'
    colors['blue'] = '\033[0;34m'
    colors['light_blue'] = '\033[0;36m'
    colors['reset'] = '\033[m'
    return colors

# Courtesy of https://gist.github.com/844388. Thanks!
class _OrderedDictYAMLLoader(yaml.Loader):
    """A YAML loader that loads mappings into ordered dictionaries."""

    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor('tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor('tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            mapping[key] = value
        return mapping

def yaml_load_ordered(f):
    return yaml.load(f, _OrderedDictYAMLLoader)

class MorphTest:
    def __init__(self, left, right, direction):
        self.left = left
        self.direction = direction 
        self.right = right

        # these will be added when running the tests
        self.ana_result = []
        self.gen_result = []
      
        self.ana_tn = True
        self.ana_fp = []
        self.ana_missing = True

        self.gen_tn = True
        self.gen_fp = []
        self.gen_missing = True

    def get_test_results(self):
      # printing test
      s = '{0:<45}\n'.format(self.left + ' ' + self.direction + ' ' + self.right) 
      
      # printing whether it passed analysis or not
      if self.ana_missing or len(self.ana_fp) or self.ana_tn == False: s += ' {red}[✗]{reset} '
      else: s += ' {green}[✓]{reset} '
      s += 'Analysis:' + ' '*26

      # print tp, tn, fp, fn 
      if self.ana_missing: s += '{red}[✗]{reset}'
      elif self.ana_missing == None: s += ' - '
      else: s += '{green}[✓]{reset}'
      s += ' '*9
      if self.ana_tn: s += '{green}[✓]{reset}'
      elif self.ana_tn == None: s += ' - '
      else: s += '{red}[✗]{reset}'
      s += ' '*9
      if not len(self.ana_fp): s += '{green}[✓]{reset}'
      else: s +=  '{red}[✗]{reset}' 
      s += ' '*9
      if self.ana_missing: s += '{red}[✗]{reset}'
      elif self.ana_missing == None: s += ' - '
      else: s += '{green}[✓]{reset}'
      s += ' '*10
      s += '\n'

      # printing whether it passed generation or not
      if self.gen_missing or len(self.gen_fp) or self.gen_tn == False: s += ' {red}[✗]{reset} '
      else: s += ' {green}[✓]{reset} '
      s += 'Generation:' + ' '*24
      
      # print tp, tn, fp, fn 
      if self.gen_missing: s += '{red}[✗]{reset}'
      elif self.gen_missing == None: s += ' - '
      else: s += '{green}[✓]{reset}'
      s += ' '*9
      if self.gen_tn: s += '{green}[✓]{reset}'
      elif self.gen_tn == None: s += ' - '
      else: s += '{red}[✗]{reset}'
      s += ' '*9
      if not len(self.gen_fp): s += '{green}[✓]{reset}'
      else: s +=  '{red}[✗]{reset}'
      s += ' '*9
      if self.gen_missing: s += '{red}[✗]{reset}'
      elif self.gen_missing == None: s += ' - '
      else: s += '{green}[✓]{reset}'
      s += '\n'

      if self.ana_missing or len(self.ana_fp): s += ' {orange}Comments: '
      if self.ana_missing: s += "test didn't return " + self.left + '. '
      if len(self.ana_fp): s += 'test incorrectly returned'
      for analysis in self.ana_fp:
        s += ' ' + analysis
      s += '\n'
      if self.ana_missing or len(self.ana_fp): s += '{reset}\n'

      return s

class Section:
    def __init__(self, title, mappings):
        self.title = title
        self.mappings = mappings 
        self.passes = 0
        self.fails = 0
        self.tests = self.populate_tests()

    def populate_tests(self):
        tests = []
        for left in self.mappings:
          for map_direction, right in self.mappings[left].items():
            if isinstance(right, list):
              for item in right:
                if map_direction in ['=>', '<=', '<=>']:
                  tests.append(MorphTest(left, item, map_direction))
                else:
                  print('Error: possible direction arrows are =>, <=, or <=>.')
                  sys.exit(1)
            else:
              if map_direction in ['=>', '<=', '<=>']:
                  tests.append(MorphTest(left, right, map_direction))
              else:
                  print('Error: possible direction arrows are =>, <=, or <=>.')
                  sys.exit(1)
       
        return tests 
    
    def __str__(self):
        s = "{orange}-"*80 + '\n{reset}' + self.title + '\n'
        s += 'Tests'+' '*30 + 'True pos    True neg    False pos   False neg\n'
        s += '{orange}-{reset}'*80 + '\n'
        for test in self.tests:
            s += test.get_test_results()
        s += 'Passes: {green}' + str(self.passes) + '{reset} / Fails: {red}' + str(self.fails) + '{reset}\n\n'
        return s

    def get_tests(self):
        return self.tests

class Results:
    def __init__(self, sections_list, morph, gen):
        self.sections = sections_list
        self.generation_dict = {}
        self.analysis_dict = {}
        for section in self.sections:
          for test in section.tests:
            if test.right in self.analysis_dict:
              self.analysis_dict[test.right].append(test.left)
            else:
              self.analysis_dict[test.right] = [test.left]
            if test.left in self.generation_dict:
              self.generation_dict[test.left].append(test.right)
            else:
              self.generation_dict[test.left] = [test.right]
        
        self.morph_path = morph
        self.gen_path = gen
        self._io = StringIO()
        self.colors = define_colors()
        self.fails = 0
        self.passes = 0

    def __str__(self):
        return self._io.getvalue()
    
    def color_write(self, string, *args, **kwargs):
        kwargs.update(self.colors)
        self._io.write(string.format(*args, **kwargs))
  
    def print_section(self, section):
        self.color_write(str(section))

    def print_final(self):
        self.color_write('Total passes: {green}' + str(self.passes) + '{reset}, ')
        self.color_write('Total fails: {red}' + str(self.fails) + '{reset}, ')
        self.color_write('Total: {light_blue}' + str(self.passes + self.fails) + '{reset}\n')

    def print_nothing(self):
        if self.fails > 0:
            return 1
        else:
            return 0

    def lookup(self):
        analysis_stream = libhfst.HfstInputStream(self.morph_path).read()
        generation_stream = libhfst.HfstInputStream(self.gen_path).read()
        for section in self.sections:  
            for test in section.tests:
               for result in analysis_stream.lookup(test.right):
                 test.ana_result.append(result[0])
               for result in generation_stream.lookup(test.left):
                 test.gen_result.append(result[0])
          
    def run_tests(self, section):
        for test in section.tests:
          print(test.left, test.direction, test.right, 'gen:', test.gen_result, 'ana:', test.ana_result)
          for result in test.ana_result:
            if test.direction == '<=' or test.direction == '<=>':
              if result == test.left:
                test.ana_missing = False
              elif result not in self.analysis_dict[test.right]:
                test.ana_fp.append(result)
              if test.direction == '<=>':
                test.ana_tn = None
            else: #test.direction is '=>'
              test.ana_missing = None
              if result == test.left:
                test.ana_tn = False
          
          for result in test.gen_result:
            if test.direction == '=>' or test.direction == '<=>':
              if result == test.right:
                test.gen_missing = False
              elif result not in self.generation_dict[test.left]:
                test.gen_fp.append(result)
              if test.direction == '<=>':
                test.gen_tn = None
            else: # test.direction is '<='
              test.gen_missing = None
              if result == test.right:
                test.gen_tn = False

       #add verbose, color, type of output etc
    def run(self):
        self.lookup()
        for section in self.sections:
            self.run_tests(section)
            #self.run_generation_tests(section)
            self.print_section(section)
        self.print_final()
        print(self)
          

def load_data(filename):
    yaml_file = open(filename, 'r')
    dictionary = yaml_load_ordered(yaml_file)
    yaml_file.close()
    
    all_sections = []
    # ensure dictionary contains only config and tests
    #getting config
    hfst_config = dictionary['Config']['hfst']
    morph = hfst_config['Morph']
    gen = hfst_config['Gen']
    #getting tests
    tests = dictionary['Tests']
    all_sections = []
    for title in tests:
        #add error if tests[title] isn't just mappings 
        section = Section(title, tests[title])
        all_sections.append(section)

    return all_sections, morph, gen

def main():
    t0 = time.time()    
    args = argument_parsing()
    sections, morph, gen = load_data(args.file)
    results = Results(sections, morph, gen)
    results.run()
    t1 = time.time()
    print(t1-t0)

if __name__ == "__main__":
    main()

