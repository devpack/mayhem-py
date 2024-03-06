class ShaderProgram:

    def __init__(self, ctx):
        self.ctx = ctx
        self.programs = {}
        self.programs['screen'] = self.get_program('screen')

    def get_program(self, shader_name):
        try:
            with open(f'shaders/{shader_name}_vs.glsl') as file:
                vertex_shader = file.read()

            with open(f'shaders/{shader_name}_fs.glsl') as file:
                fragment_shader = file.read()

            program = self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)
            return program
        except Exception as e:
            print("Failed to load %s : %s" % (shader_name, repr(e)))
            return None

    def destroy(self):
        for program in self.programs.values():
            if program:
                program.release()