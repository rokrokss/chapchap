import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { fetchAnalyzeResumeStream } from '@/services/resume';
import { Loader2 } from 'lucide-react';
import { useAnimatedText } from '@/components/animated-text';

const formSchema = z.object({
  resume: z.custom<File>(file => file instanceof File && file.type === 'application/pdf', {
    message: 'PDF 파일만 업로드 가능합니다.',
  }),
});

const JobMatcher = () => {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const animatedText = useAnimatedText(summary);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      resume: undefined,
    },
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    console.log(values);
    setLoading(true);
    setSummary('');

    const reader = await fetchAnalyzeResumeStream(values.resume);
    const decoder = new TextDecoder('utf-8');

    if (!reader) return;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const chunkObj = JSON.parse(chunk.replace(/\n/g, '\\n'));
      setSummary(prev => prev + chunkObj['chunk']);
    }

    setLoading(false);
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-6">
      <div className="w-full max-w-3xl mx-auto">
        <Form {...form}>
          <Label className="mb-3 mt-2">
            이력서 분석 {'>'} 공고 매칭 {'>'} 스킬갭 분석 {'>'} AI커버레터
          </Label>
          <FormDescription className="mb-1">
            PDF 형식의 이력서를 분석할 수 있습니다. 이력서와 분석 결과는 서버에 보관되지 않습니다.
          </FormDescription>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex w-full items-center gap-1">
            <FormField
              control={form.control}
              name="resume"
              render={({ field: { value, onChange, ...fieldProps } }) => (
                <FormItem className="w-full">
                  <FormControl>
                    <Input
                      {...fieldProps}
                      type="file"
                      accept="image/*, application/pdf"
                      onChange={event => onChange(event.target.files && event.target.files[0])}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" className="self-start" disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : '분석 시작'}
            </Button>
          </form>
        </Form>
        {summary || loading ? (
          <div className="mt-4">
            <Label>이력서 요약</Label>
            <div className="mt-2 p-4 border rounded-md text-sm" style={{ whiteSpace: 'pre-wrap' }}>
              {animatedText || <Loader2 className="w-4 h-4 animate-spin" />}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default JobMatcher;
